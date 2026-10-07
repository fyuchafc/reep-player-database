import csv
import json
import os
import time
from datetime import datetime, timezone

import duckdb
import requests


# ============================================================
# REEP → WIKIDATA DOB GRAPHQL AUDIT
# ============================================================
#
# READ-ONLY:
#   - Source REEP database is NEVER modified.
#   - v1.0.0 master is NEVER modified.
#
# Purpose:
#   Audit confirmed REEP DOB-linked QIDs against Wikidata P569.
#
# Important:
#   Wikidata may automatically redirect an old QID to another QID.
#   Example:
#
#       Q138949315 → Q131757414
#
#   The original REEP QID must be preserved while the resolved
#   Wikidata QID and DOB are recorded.
#
# ============================================================


SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = "output"

PROGRESS_FILE = os.path.join(
    OUTPUT_DIR,
    "reep-wikidata-dob-graphql-progress.json"
)

CSV_FILE = os.path.join(
    OUTPUT_DIR,
    "reep-wikidata-dob-graphql-audit.csv"
)

JSON_FILE = os.path.join(
    OUTPUT_DIR,
    "reep-wikidata-dob-graphql-audit.json"
)

GRAPHQL_URL = (
    "https://www.wikidata.org/w/api.php"
    "?action=wbgraphql&format=json"
)

USER_AGENT = (
    "FyuchaFC-REEP-DOB-Audit/1.0 "
    "(https://github.com/fyuchafc/reep-player-database)"
)

BATCH_SIZE = 50
REQUEST_TIMEOUT = 90
SUCCESS_DELAY_SECONDS = 3

MAX_RETRIES = 3
RETRY_DELAYS = [30, 60, 120]


# ============================================================
# GRAPHQL QUERY
# ============================================================

GRAPHQL_QUERY = """
query GetItems($ids: [ItemId!]!) {
  itemsById(ids: $ids) {
    id
    statements(propertyId: "P569") {
      value {
        ... on TimeValue {
          time
          precision
        }
      }
      rank
    }
  }
}
"""


# ============================================================
# HELPERS
# ============================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_progress():
    if not os.path.exists(PROGRESS_FILE):
        return {
            "completed_batches": [],
            "results": {},
            "redirects": {},
            "updated_at": None
        }

    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    completed = data.get("completed_batches", [])

    # Compatibility with the earlier progress format where
    # completed_batches could be stored as an integer.
    if isinstance(completed, int):
        completed = list(range(1, completed + 1))

    data["completed_batches"] = sorted(
        set(int(x) for x in completed)
    )

    if "results" not in data:
        data["results"] = {}

    if "redirects" not in data:
        data["redirects"] = {}

    return data


def save_progress(progress):
    progress["updated_at"] = utc_now()

    temp_file = PROGRESS_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            progress,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temp_file, PROGRESS_FILE)


def get_reep_qids():
    print("Opening REEP source database read-only...")

    con = duckdb.connect(
        SOURCE_DB,
        read_only=True
    )

    query = """
        SELECT DISTINCT
            p.reep_id,
            p.label,
            ol.qid
        FROM players p
        INNER JOIN overlay_links ol
            ON ol.reep_id = p.reep_id
        WHERE
            ol.qid IS NOT NULL
            AND TRIM(ol.qid) <> ''
            AND LOWER(
                TRIM(ol.dob_check)
            ) = 'dob-agrees'
        ORDER BY
            ol.qid,
            p.reep_id
    """

    rows = con.execute(query).fetchall()

    con.close()

    return rows


def parse_time_value(value):
    if not value:
        return None, None

    time_value = value.get("time")
    precision = value.get("precision")

    if not time_value:
        return None, precision

    # Wikidata normally returns:
    # +1999-03-29T00:00:00Z
    #
    # Remove leading + and time component.
    clean = time_value.lstrip("+")

    if "T" in clean:
        clean = clean.split("T", 1)[0]

    return clean, precision


def precision_name(precision):
    if precision == 11:
        return "day"
    if precision == 10:
        return "month"
    if precision == 9:
        return "year"
    return "other"


def classify_claims(statements):
    claims = []

    for statement in statements or []:
        value = statement.get("value") or {}

        dob, precision = parse_time_value(value)

        if dob is None:
            continue

        rank = str(
            statement.get("rank", "")
        ).upper()

        claims.append({
            "dob": dob,
            "precision": precision,
            "precision_name": precision_name(precision),
            "rank": rank
        })

    return claims


def graphql_request(qids):
    payload = {
        "query": GRAPHQL_QUERY,
        "variables": {
            "ids": qids
        }
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    response = requests.post(
        GRAPHQL_URL,
        json=payload,
        headers=headers,
        timeout=REQUEST_TIMEOUT
    )

    return response


# ============================================================
# MAIN GRAPHQL BATCH
# ============================================================

def request_batch(qids, stats):

    for attempt in range(MAX_RETRIES + 1):

        try:
            response = graphql_request(qids)

            stats["requests"] += 1

            if response.status_code == 429:
                stats["http_429"] += 1

                if attempt >= MAX_RETRIES:
                    raise RuntimeError(
                        "HTTP 429 after maximum retries."
                    )

                delay = RETRY_DELAYS[
                    min(attempt, len(RETRY_DELAYS) - 1)
                ]

                print(
                    f"  HTTP 429. Waiting {delay} seconds "
                    f"before retry {attempt + 1}/{MAX_RETRIES}..."
                )

                time.sleep(delay)
                stats["retries"] += 1
                continue

            if response.status_code >= 500:
                stats["http_5xx"] += 1

                if attempt >= MAX_RETRIES:
                    raise RuntimeError(
                        f"HTTP {response.status_code} "
                        f"after maximum retries."
                    )

                delay = RETRY_DELAYS[
                    min(attempt, len(RETRY_DELAYS) - 1)
                ]

                print(
                    f"  HTTP {response.status_code}. "
                    f"Waiting {delay} seconds before retry "
                    f"{attempt + 1}/{MAX_RETRIES}..."
                )

                time.sleep(delay)
                stats["retries"] += 1
                continue

            response.raise_for_status()

            data = response.json()

            if "errors" in data:
                stats["graphql_errors"] += 1

                errors = data.get("errors", [])

                error_text = json.dumps(
                    errors,
                    ensure_ascii=False
                )

                # Schema errors should NEVER be retried.
                schema_error_patterns = [
                    'Variable "$ids"',
                    "Unknown type",
                    "Cannot query field",
                    "Unknown argument",
                    "Unknown field"
                ]

                if any(
                    pattern in error_text
                    for pattern in schema_error_patterns
                ):
                    raise RuntimeError(
                        "GraphQL schema error: "
                        + error_text
                    )

                if attempt >= MAX_RETRIES:
                    raise RuntimeError(
                        "GraphQL error after maximum retries: "
                        + error_text
                    )

                delay = RETRY_DELAYS[
                    min(attempt, len(RETRY_DELAYS) - 1)
                ]

                print(
                    "  Temporary GraphQL error: "
                    + error_text
                )

                print(
                    f"  Waiting {delay} seconds before retry "
                    f"{attempt + 1}/{MAX_RETRIES}..."
                )

                time.sleep(delay)
                stats["retries"] += 1
                continue

            items = (
                data.get("data", {})
                .get("itemsById")
            )

            if items is None:
                raise RuntimeError(
                    "GraphQL returned no itemsById data."
                )

            # ------------------------------------------------
            # REDIRECT HANDLING
            # ------------------------------------------------
            #
            # Wikidata may return:
            #
            # requested: Q138949315
            # returned:  Q131757414
            #
            # The GraphQL response also provides:
            #
            # extensions.redirects = {
            #     "Q138949315": "Q131757414"
            # }
            #
            # Therefore a returned ID that differs from the
            # requested ID is NOT treated as missing.
            # ------------------------------------------------

            redirects = (
                data.get("extensions", {})
                .get("redirects", {})
            )

            normalized_redirects = {}

            for old_qid, new_qid in redirects.items():
                normalized_redirects[
                    str(old_qid)
                ] = str(new_qid)

            returned_items = {}

            for item in items:
                if not item:
                    continue

                returned_id = item.get("id")

                if returned_id:
                    returned_items[
                        str(returned_id)
                    ] = item

            resolved_to_original = {}

            for original_qid, resolved_qid in normalized_redirects.items():
                resolved_to_original.setdefault(
                    resolved_qid,
                    []
                ).append(original_qid)

            # ------------------------------------------------
            # Build complete requested-QID results.
            # ------------------------------------------------

            batch_results = {}
            missing = []

            for requested_qid in qids:

                requested_qid = str(requested_qid)

                # Normal case:
                if requested_qid in returned_items:

                    item = returned_items[
                        requested_qid
                    ]

                    claims = classify_claims(
                        item.get("statements", [])
                    )

                    batch_results[requested_qid] = {
                        "requested_qid": requested_qid,
                        "resolved_qid": requested_qid,
                        "redirected": False,
                        "entity_found": True,
                        "dob_claims": claims
                    }

                    continue

                # Redirect case:
                resolved_qid = normalized_redirects.get(
                    requested_qid
                )

                if resolved_qid and resolved_qid in returned_items:

                    item = returned_items[
                        resolved_qid
                    ]

                    claims = classify_claims(
                        item.get("statements", [])
                    )

                    batch_results[requested_qid] = {
                        "requested_qid": requested_qid,
                        "resolved_qid": resolved_qid,
                        "redirected": True,
                        "entity_found": True,
                        "dob_claims": claims
                    }

                    continue

                # If the redirect chain has another level,
                # follow it defensively.
                current_qid = requested_qid
                visited = set()

                while current_qid in normalized_redirects:

                    if current_qid in visited:
                        break

                    visited.add(current_qid)

                    current_qid = normalized_redirects[
                        current_qid
                    ]

                    if current_qid in returned_items:

                        item = returned_items[
                            current_qid
                        ]

                        claims = classify_claims(
                            item.get("statements", [])
                        )

                        batch_results[requested_qid] = {
                            "requested_qid": requested_qid,
                            "resolved_qid": current_qid,
                            "redirected": True,
                            "entity_found": True,
                            "dob_claims": claims
                        }

                        break

                if requested_qid not in batch_results:
                    missing.append(requested_qid)

            # ------------------------------------------------
            # Only truly missing requested IDs cause failure.
            # ------------------------------------------------

            if missing:
                stats["incomplete_batches"] += 1

                print()
                print(
                    "  ERROR:"
                )
                print(
                    "  GraphQL returned an incomplete batch. "
                    f"Missing {len(missing)} QIDs. "
                    f"Examples: {', '.join(missing[:10])}"
                )

                print()
                print(
                    "  Batch was NOT marked complete."
                )

                return None

            return batch_results

        except requests.exceptions.Timeout:
            stats["timeouts"] += 1

            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "Request timed out after maximum retries."
                )

            delay = RETRY_DELAYS[
                min(attempt, len(RETRY_DELAYS) - 1)
            ]

            print(
                f"  Timeout. Waiting {delay} seconds "
                f"before retry {attempt + 1}/{MAX_RETRIES}..."
            )

            time.sleep(delay)
            stats["retries"] += 1

        except requests.exceptions.ConnectionError:
            stats["connection_errors"] += 1

            if attempt >= MAX_RETRIES:
                raise RuntimeError(
                    "Connection error after maximum retries."
                )

            delay = RETRY_DELAYS[
                min(attempt, len(RETRY_DELAYS) - 1)
            ]

            print(
                f"  Connection error. Waiting {delay} seconds "
                f"before retry {attempt + 1}/{MAX_RETRIES}..."
            )

            time.sleep(delay)
            stats["retries"] += 1

    raise RuntimeError(
        "Batch failed unexpectedly."
    )


# ============================================================
# OUTPUT
# ============================================================

def build_output_rows(reep_rows, results):

    rows = []

    for reep_id, label, qid in reep_rows:

        qid = str(qid)

        result = results.get(qid)

        if not result:
            continue

        claims = result.get(
            "dob_claims",
            []
        )

        day_claims = [
            c for c in claims
            if c["precision"] == 11
        ]

        month_claims = [
            c for c in claims
            if c["precision"] == 10
        ]

        year_claims = [
            c for c in claims
            if c["precision"] == 9
        ]

        preferred = [
            c for c in claims
            if c["rank"] == "PREFERRED"
        ]

        normal = [
            c for c in claims
            if c["rank"] == "NORMAL"
        ]

        deprecated = [
            c for c in claims
            if c["rank"] == "DEPRECATED"
        ]

        rows.append({
            "reep_id": reep_id,
            "label": label,
            "source_qid": qid,
            "resolved_qid": result.get(
                "resolved_qid"
            ),
            "redirected": result.get(
                "redirected",
                False
            ),
            "entity_found": result.get(
                "entity_found",
                False
            ),
            "dob_claim_count": len(claims),
            "dob_values": ";".join(
                sorted(
                    set(
                        c["dob"]
                        for c in claims
                    )
                )
            ),
            "day_precision_count": len(
                day_claims
            ),
            "month_precision_count": len(
                month_claims
            ),
            "year_precision_count": len(
                year_claims
            ),
            "preferred_claim_count": len(
                preferred
            ),
            "normal_claim_count": len(
                normal
            ),
            "deprecated_claim_count": len(
                deprecated
            ),
            "multiple_p569": len(claims) > 1
        })

    return rows


def write_outputs(reep_rows, results):

    rows = build_output_rows(
        reep_rows,
        results
    )

    fieldnames = [
        "reep_id",
        "label",
        "source_qid",
        "resolved_qid",
        "redirected",
        "entity_found",
        "dob_claim_count",
        "dob_values",
        "day_precision_count",
        "month_precision_count",
        "year_precision_count",
        "preferred_claim_count",
        "normal_claim_count",
        "deprecated_claim_count",
        "multiple_p569"
    ]

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            rows,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    total_qids,
    completed_batches,
    total_batches,
    results,
    stats
):

    entities_found = 0
    no_p569 = 0
    single_p569 = 0
    multiple_p569 = 0

    day_precision = 0
    month_precision = 0
    year_precision = 0
    other_precision = 0

    preferred = 0
    normal = 0
    deprecated = 0

    redirects = 0

    for result in results.values():

        if result.get("entity_found"):
            entities_found += 1

        claims = result.get(
            "dob_claims",
            []
        )

        if not claims:
            no_p569 += 1
        elif len(claims) == 1:
            single_p569 += 1
        else:
            multiple_p569 += 1

        for claim in claims:

            precision = claim.get(
                "precision"
            )

            if precision == 11:
                day_precision += 1
            elif precision == 10:
                month_precision += 1
            elif precision == 9:
                year_precision += 1
            else:
                other_precision += 1

            rank = claim.get("rank")

            if rank == "PREFERRED":
                preferred += 1
            elif rank == "NORMAL":
                normal += 1
            elif rank == "DEPRECATED":
                deprecated += 1

        if result.get("redirected"):
            redirects += 1

    print()
    print("=" * 70)
    print("GRAPHQL DOB AUDIT SUMMARY")
    print("=" * 70)

    print(
        f"Total unique QIDs:          {total_qids:,}"
    )

    print(
        f"Batches completed:          "
        f"{completed_batches:,} / {total_batches:,}"
    )

    print(
        f"QIDs successfully audited:  "
        f"{len(results):,}"
    )

    print(
        f"QIDs not yet audited:       "
        f"{total_qids - len(results):,}"
    )

    print(
        f"Entities found:             "
        f"{entities_found:,}"
    )

    print(
        f"No P569:                    "
        f"{no_p569:,}"
    )

    print(
        f"Single P569:                "
        f"{single_p569:,}"
    )

    print(
        f"Multiple P569:              "
        f"{multiple_p569:,}"
    )

    print(
        f"Day precision:              "
        f"{day_precision:,}"
    )

    print(
        f"Month precision:            "
        f"{month_precision:,}"
    )

    print(
        f"Year precision:             "
        f"{year_precision:,}"
    )

    print(
        f"Other precision:            "
        f"{other_precision:,}"
    )

    print(
        f"Preferred claims:           "
        f"{preferred:,}"
    )

    print(
        f"Normal claims:              "
        f"{normal:,}"
    )

    print(
        f"Deprecated claims:          "
        f"{deprecated:,}"
    )

    print(
        f"Redirected QIDs:            "
        f"{redirects:,}"
    )

    print()

    print(
        f"Requests:                   "
        f"{stats['requests']:,}"
    )

    print(
        f"Retries:                    "
        f"{stats['retries']:,}"
    )

    print(
        f"HTTP 429:                   "
        f"{stats['http_429']:,}"
    )

    print(
        f"HTTP 5xx:                   "
        f"{stats['http_5xx']:,}"
    )

    print(
        f"Timeouts:                   "
        f"{stats['timeouts']:,}"
    )

    print(
        f"Connection errors:          "
        f"{stats['connection_errors']:,}"
    )

    print(
        f"GraphQL errors:             "
        f"{stats['graphql_errors']:,}"
    )

    print(
        f"Incomplete batches:         "
        f"{stats['incomplete_batches']:,}"
    )

    print()

    print(
        f"CSV:      {CSV_FILE}"
    )

    print(
        f"JSON:     {JSON_FILE}"
    )

    print(
        f"Progress:  {PROGRESS_FILE}"
    )

    print()

    print(
        "No REEP database changes were made."
    )

    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    ensure_output_dir()

    print()
    print(
        "REEP → WIKIDATA DOB GRAPHQL AUDIT"
    )
    print("=" * 70)
    print()
    print(
        "READ-ONLY — source REEP database "
        "will NOT be modified."
    )
    print()

    reep_rows = get_reep_qids()

    total_player_rows = len(reep_rows)

    unique_qids = sorted(
        set(
            str(row[2])
            for row in reep_rows
            if row[2]
        )
    )

    total_qids = len(unique_qids)

    batches = [
        unique_qids[i:i + BATCH_SIZE]
        for i in range(
            0,
            total_qids,
            BATCH_SIZE
        )
    ]

    total_batches = len(batches)

    print(
        f"Confirmed REEP player rows: "
        f"{total_player_rows:,}"
    )

    print(
        f"Unique Wikidata QIDs: "
        f"{total_qids:,}"
    )

    print(
        f"Total batches: "
        f"{total_batches:,}"
    )

    progress = load_progress()

    completed_batches = set(
        progress.get(
            "completed_batches",
            []
        )
    )

    results = progress.get(
        "results",
        {}
    )

    print(
        f"Previously completed: "
        f"{len(completed_batches):,}"
    )

    print(
        f"Existing QID results: "
        f"{len(results):,}"
    )

    print(
        f"Remaining batches: "
        f"{total_batches - len(completed_batches):,}"
    )

    print()

    stats = {
        "requests": 0,
        "retries": 0,
        "http_429": 0,
        "http_5xx": 0,
        "timeouts": 0,
        "connection_errors": 0,
        "graphql_errors": 0,
        "incomplete_batches": 0
    }

    session_results_changed = False

    for batch_number, qid_batch in enumerate(
        batches,
        start=1
    ):

        if batch_number in completed_batches:
            continue

        print(
            f"Batch {batch_number}/{total_batches} "
            f"({len(qid_batch)} QIDs)..."
        )

        try:

            batch_results = request_batch(
                qid_batch,
                stats
            )

            if batch_results is None:
                save_progress(progress)

                write_outputs(
                    reep_rows,
                    results
                )

                print_summary(
                    total_qids,
                    len(completed_batches),
                    total_batches,
                    results,
                    stats
                )

                return

            # Save results keyed by the ORIGINAL requested QID.
            for requested_qid, result in batch_results.items():

                results[
                    requested_qid
                ] = result

            progress["results"] = results

            completed_batches.add(
                batch_number
            )

            progress[
                "completed_batches"
            ] = sorted(
                completed_batches
            )

            save_progress(progress)

            session_results_changed = True

            print(
                "  Completed and progress saved."
            )

            if batch_number < total_batches:

                print(
                    f"  Waiting "
                    f"{SUCCESS_DELAY_SECONDS} seconds..."
                )

                time.sleep(
                    SUCCESS_DELAY_SECONDS
                )

        except KeyboardInterrupt:

            print()
            print(
                "Audit interrupted by user."
            )

            save_progress(progress)

            write_outputs(
                reep_rows,
                results
            )

            print_summary(
                total_qids,
                len(completed_batches),
                total_batches,
                results,
                stats
            )

            return

        except Exception as e:

            print()
            print(
                "  ERROR:"
            )

            print(
                f"  {e}"
            )

            print()

            print(
                "  Batch was NOT marked complete."
            )

            save_progress(progress)

            write_outputs(
                reep_rows,
                results
            )

            print_summary(
                total_qids,
                len(completed_batches),
                total_batches,
                results,
                stats
            )

            return

    progress["results"] = results
    progress[
        "completed_batches"
    ] = sorted(
        completed_batches
    )

    save_progress(progress)

    write_outputs(
        reep_rows,
        results
    )

    print()
    print(
        "AUDIT COMPLETE — ALL BATCHES PROCESSED."
    )

    print_summary(
        total_qids,
        len(completed_batches),
        total_batches,
        results,
        stats
    )


if __name__ == "__main__":
    main()