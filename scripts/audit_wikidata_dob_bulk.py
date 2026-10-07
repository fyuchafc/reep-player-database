#!/usr/bin/env python3

"""
REEP -> WIKIDATA DOB BULK AUDIT
================================

Purpose:
    Audit Wikidata date-of-birth (P569) claims for REEP players
    that already have confirmed Wikidata QID evidence.

IMPORTANT:
    - Source REEP database is READ-ONLY.
    - Existing successful progress is preserved.
    - Existing 50-QID batch numbering is preserved.
    - Incomplete API responses are NEVER marked complete.
    - Wikidata maxlag is handled conservatively.
    - Multiple P569 claims are preserved.
    - This script does NOT modify the REEP master database.

Resume file:
    output/reep-wikidata-dob-progress.json

Final outputs:
    output/reep-wikidata-dob-audit.csv
    output/reep-wikidata-dob-audit.json
"""

from __future__ import annotations

import csv
import gzip
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


# ============================================================
# PATHS
# ============================================================

SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = "output"

PROGRESS_FILE = os.path.join(
    OUTPUT_DIR,
    "reep-wikidata-dob-progress.json"
)

CSV_FILE = os.path.join(
    OUTPUT_DIR,
    "reep-wikidata-dob-audit.csv"
)

JSON_FILE = os.path.join(
    OUTPUT_DIR,
    "reep-wikidata-dob-audit.json"
)


# ============================================================
# WIKIDATA SETTINGS
# ============================================================

API_URL = "https://www.wikidata.org/w/api.php"

# Anonymous wbgetentities limit.
BATCH_SIZE = 50

# Deliberate pause after every successful batch.
SUCCESS_DELAY_SECONDS = 8

# Maximum retries for a temporary failure.
MAX_RETRIES = 10

# Network timeout for an individual request.
REQUEST_TIMEOUT = 90

# Wikidata maxlag setting.
MAXLAG_SECONDS = 5

# Descriptive User-Agent.
USER_AGENT = (
    "Fyucha REEP Player Database/1.1 "
    "(Wikidata DOB audit; "
    "read-only research)"
)

# Conservative retry schedule.
MAXLAG_WAIT_SCHEDULE = [
    60,
    120,
    180,
    300,
    300,
    600,
    600,
    900,
    900,
    1200,
]


# ============================================================
# RUN STATISTICS
# ============================================================

stats = {
    "requests": 0,
    "retries": 0,
    "maxlag_events": 0,
    "http_429_events": 0,
    "http_5xx_events": 0,
    "timeout_errors": 0,
    "connection_errors": 0,
    "incomplete_responses": 0,
    "completed_batches_this_run": 0,
}


# ============================================================
# GENERAL HELPERS
# ============================================================

def now_utc() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def ensure_output_dir() -> None:
    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )


def atomic_write_json(
    path: str,
    data: Any
) -> None:

    temp_path = path + ".tmp"

    with open(
        temp_path,
        "w",
        encoding="utf-8"
    ) as handle:

        json.dump(
            data,
            handle,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_path,
        path
    )


# ============================================================
# PROGRESS
# ============================================================

def load_progress() -> dict[str, Any]:

    if not os.path.exists(
        PROGRESS_FILE
    ):

        return {
            "version": 2,
            "created_at": now_utc(),
            "updated_at": now_utc(),
            "completed_batches": [],
            "results": {},
        }

    with open(
        PROGRESS_FILE,
        "r",
        encoding="utf-8"
    ) as handle:

        progress = json.load(
            handle
        )

    if not isinstance(
        progress,
        dict
    ):

        raise RuntimeError(
            "Progress file is not a JSON object."
        )

    if "results" not in progress:
        progress["results"] = {}

    if not isinstance(
        progress["results"],
        dict
    ):

        raise RuntimeError(
            "Progress file has an invalid results structure."
        )

    return progress


def get_completed_batches(
    progress: dict[str, Any]
) -> set[int]:

    raw = progress.get(
        "completed_batches",
        []
    )

    # --------------------------------------------------------
    # OLD FORMAT
    #
    # completed_batches = 740
    # --------------------------------------------------------

    if isinstance(
        raw,
        int
    ):

        if raw <= 0:
            return set()

        print(
            f"Detected old progress format: "
            f"{raw} completed batches."
        )

        print(
            f"Restoring completed batches "
            f"1 through {raw}."
        )

        return set(
            range(
                1,
                raw + 1
            )
        )

    # --------------------------------------------------------
    # NEW FORMAT
    #
    # completed_batches = [1,2,3,...]
    # --------------------------------------------------------

    if isinstance(
        raw,
        list
    ):

        completed = set()

        for value in raw:

            try:
                number = int(
                    value
                )

                if number > 0:
                    completed.add(
                        number
                    )

            except (
                TypeError,
                ValueError
            ):
                continue

        return completed

    raise RuntimeError(
        "Unknown completed_batches format "
        "in progress file."
    )


def save_progress(
    progress: dict[str, Any],
    completed_batches: set[int]
) -> None:

    progress["version"] = 2

    progress["updated_at"] = now_utc()

    progress["completed_batches"] = sorted(
        completed_batches
    )

    atomic_write_json(
        PROGRESS_FILE,
        progress
    )


# ============================================================
# REEP DATABASE
# ============================================================

def load_reep_qids() -> list[dict[str, str]]:

    """
    Load REEP players that have:

        - a Wikidata QID
        - previous REEP DOB status = dob-agrees

    IMPORTANT:
        The players table does NOT contain entity_type.
        Do not add p.entity_type to this query.
    """

    try:

        import duckdb

    except ImportError:

        print()
        print(
            "ERROR: DuckDB Python package is not installed."
        )

        print()
        print(
            "Install it with:"
        )

        print()
        print(
            "python -m pip install duckdb"
        )

        print()

        sys.exit(1)

    if not os.path.exists(
        SOURCE_DB
    ):

        raise FileNotFoundError(
            "Source database not found:\n"
            + SOURCE_DB
        )

    print(
        "Opening REEP source database read-only..."
    )

    connection = duckdb.connect(
        SOURCE_DB,
        read_only=True
    )

    try:

        # ----------------------------------------------------
        # Check required tables.
        # ----------------------------------------------------

        tables = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
        ).fetchall()

        table_names = {
            row[0]
            for row in tables
        }

        required = {
            "players",
            "overlay_links"
        }

        missing = (
            required
            - table_names
        )

        if missing:

            raise RuntimeError(
                "Missing required REEP tables: "
                + ", ".join(
                    sorted(missing)
                )
            )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # players table has no entity_type column.
        #
        # We therefore filter only on the DOB/QID evidence
        # available through overlay_links.
        # ----------------------------------------------------

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

        rows = connection.execute(
            query
        ).fetchall()

    finally:

        connection.close()

    records = []

    for (
        reep_id,
        label,
        qid
    ) in rows:

        if not qid:
            continue

        qid = str(
            qid
        ).strip()

        if not qid.startswith(
            "Q"
        ):
            continue

        records.append(
            {
                "reep_id": str(
                    reep_id
                ),
                "label": str(
                    label or ""
                ),
                "qid": qid,
            }
        )

    return records


# ============================================================
# BATCH CREATION
# ============================================================

def make_batches(
    qids: list[str]
) -> list[list[str]]:

    return [
        qids[
            i:i + BATCH_SIZE
        ]
        for i in range(
            0,
            len(qids),
            BATCH_SIZE
        )
    ]


# ============================================================
# HTTP HELPERS
# ============================================================

def read_response_bytes(
    response: Any
) -> bytes:

    raw = response.read()

    encoding = (
        response.headers.get(
            "Content-Encoding",
            ""
        )
        .lower()
        .strip()
    )

    if "gzip" in encoding:

        raw = gzip.decompress(
            raw
        )

    return raw


def parse_json_response(
    raw: bytes
) -> dict[str, Any]:

    if not raw:

        raise RuntimeError(
            "Wikidata returned an empty response."
        )

    try:

        text = raw.decode(
            "utf-8"
        )

    except UnicodeDecodeError as exc:

        raise RuntimeError(
            "Unable to decode Wikidata response: "
            f"{exc}"
        ) from exc

    try:

        data = json.loads(
            text
        )

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "Invalid JSON returned by Wikidata: "
            f"{exc}"
        ) from exc

    if not isinstance(
        data,
        dict
    ):

        raise RuntimeError(
            "Wikidata returned JSON that "
            "is not an object."
        )

    return data


def extract_retry_after(
    headers: Any
) -> int | None:

    value = headers.get(
        "Retry-After"
    )

    if value is None:
        return None

    try:

        seconds = int(
            float(
                value
            )
        )

        if seconds < 0:
            return None

        return seconds

    except (
        TypeError,
        ValueError
    ):

        return None


def build_request(
    qids: list[str]
) -> urllib.request.Request:

    params = {
        "action": "wbgetentities",
        "ids": "|".join(qids),
        "props": "claims",
        "format": "json",
        "formatversion": "2",
        "maxlag": str(
            MAXLAG_SECONDS
        ),
    }

    url = (
        API_URL
        + "?"
        + urllib.parse.urlencode(
            params
        )
    )

    headers = {
        "User-Agent": USER_AGENT,
        "Api-User-Agent": USER_AGENT,
        "Accept-Encoding": "gzip,deflate",
        "Accept": "application/json",
        "Connection": "close",
    }

    return urllib.request.Request(
        url,
        headers=headers,
        method="GET"
    )


# ============================================================
# TEMPORARY ERROR
# ============================================================

class TemporaryWikidataError(
    Exception
):

    def __init__(
        self,
        message: str,
        wait_seconds: int | None = None
    ):

        super().__init__(
            message
        )

        self.wait_seconds = (
            wait_seconds
        )


# ============================================================
# WIKIDATA REQUEST
# ============================================================

def request_wikidata_batch(
    qids: list[str]
) -> dict[str, Any]:

    request = build_request(
        qids
    )

    stats["requests"] += 1

    try:

        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT
        ) as response:

            status = response.status

            raw = read_response_bytes(
                response
            )

            if status != 200:

                raise urllib.error.HTTPError(
                    request.full_url,
                    status,
                    f"HTTP {status}",
                    response.headers,
                    None
                )

            data = parse_json_response(
                raw
            )

    except urllib.error.HTTPError as exc:

        # ----------------------------------------------------
        # HTTP 429
        # ----------------------------------------------------

        if exc.code == 429:

            stats[
                "http_429_events"
            ] += 1

            retry_after = (
                extract_retry_after(
                    exc.headers
                )
            )

            if retry_after is None:
                retry_after = 300

            raise TemporaryWikidataError(
                "HTTP 429 Too Many Requests",
                wait_seconds=retry_after
            )

        # ----------------------------------------------------
        # HTTP 5xx
        # ----------------------------------------------------

        if 500 <= exc.code <= 599:

            stats[
                "http_5xx_events"
            ] += 1

            raise TemporaryWikidataError(
                f"HTTP {exc.code} server error",
                wait_seconds=None
            )

        raise RuntimeError(
            f"Wikidata HTTP error "
            f"{exc.code}: {exc.reason}"
        )

    except socket.timeout as exc:

        stats[
            "timeout_errors"
        ] += 1

        raise TemporaryWikidataError(
            "Network timeout",
            wait_seconds=None
        ) from exc

    except TimeoutError as exc:

        stats[
            "timeout_errors"
        ] += 1

        raise TemporaryWikidataError(
            "Network timeout",
            wait_seconds=None
        ) from exc

    except urllib.error.URLError as exc:

        stats[
            "connection_errors"
        ] += 1

        raise TemporaryWikidataError(
            f"Connection error: {exc.reason}",
            wait_seconds=None
        ) from exc

    # --------------------------------------------------------
    # API-level errors
    # --------------------------------------------------------

    if "error" in data:

        error = data.get(
            "error"
        )

        if isinstance(
            error,
            dict
        ):

            code = str(
                error.get(
                    "code",
                    ""
                )
            )

            info = str(
                error.get(
                    "info",
                    ""
                )
            )

            message = (
                f"Wikidata API error "
                f"{code}: {info}"
            )

        else:

            message = (
                f"Wikidata API error: "
                f"{error}"
            )

        if "maxlag" in (
            message.lower()
        ):

            stats[
                "maxlag_events"
            ] += 1

            raise TemporaryWikidataError(
                message,
                wait_seconds=None
            )

        raise RuntimeError(
            message
        )

    # --------------------------------------------------------
    # entities must exist
    # --------------------------------------------------------

    entities = data.get(
        "entities"
    )

    if not isinstance(
        entities,
        list
    ):

        stats[
            "incomplete_responses"
        ] += 1

        raise TemporaryWikidataError(
            "Wikidata returned no complete "
            "'entities' list.",
            wait_seconds=None
        )

    # --------------------------------------------------------
    # Verify every requested QID.
    # --------------------------------------------------------

    returned_ids = set()

    for entity in entities:

        if not isinstance(
            entity,
            dict
        ):
            continue

        entity_id = entity.get(
            "id"
        )

        if entity_id:

            returned_ids.add(
                str(entity_id)
            )

    requested_ids = set(
        qids
    )

    # Wikidata can explicitly mark an entity as missing.
    explicit_missing = set()

    for entity in entities:

        if not isinstance(
            entity,
            dict
        ):
            continue

        entity_id = entity.get(
            "id"
        )

        if (
            entity_id
            and entity.get(
                "missing"
            ) is not None
        ):

            explicit_missing.add(
                str(entity_id)
            )

    accepted_ids = (
        returned_ids
        | explicit_missing
    )

    missing_from_response = (
        requested_ids
        - accepted_ids
    )

    if missing_from_response:

        stats[
            "incomplete_responses"
        ] += 1

        sample = sorted(
            missing_from_response
        )[:10]

        raise TemporaryWikidataError(
            "Incomplete Wikidata response. "
            f"Missing {len(missing_from_response)} "
            "requested QIDs. "
            "Examples: "
            + ", ".join(sample),
            wait_seconds=None
        )

    return data


# ============================================================
# DATE PARSING
# ============================================================

def parse_wikidata_time(
    value: Any
) -> tuple[str | None, int | None]:

    if not isinstance(
        value,
        dict
    ):

        return None, None

    time_value = value.get(
        "time"
    )

    precision = value.get(
        "precision"
    )

    if not time_value:

        return None, precision

    text = str(
        time_value
    )

    if text.startswith(
        "+"
    ):

        text = text[1:]

    if text.endswith(
        "Z"
    ):

        text = text[:-1]

    if "T" in text:

        text = text.split(
            "T",
            1
        )[0]

    return (
        text,
        precision
    )


def precision_name(
    precision: int | None
) -> str:

    if precision == 11:
        return "day"

    if precision == 10:
        return "month"

    if precision == 9:
        return "year"

    if precision is None:
        return "unknown"

    return "other"


# ============================================================
# P569 EXTRACTION
# ============================================================

def extract_p569_claims(
    entity: dict[str, Any]
) -> list[dict[str, Any]]:

    claims = entity.get(
        "claims"
    )

    if not isinstance(
        claims,
        dict
    ):

        return []

    p569 = claims.get(
        "P569"
    )

    if not isinstance(
        p569,
        list
    ):

        return []

    results = []

    for index, claim in enumerate(
        p569,
        start=1
    ):

        if not isinstance(
            claim,
            dict
        ):
            continue

        rank = str(
            claim.get(
                "rank",
                ""
            )
        )

        mainsnak = claim.get(
            "mainsnak"
        )

        if not isinstance(
            mainsnak,
            dict
        ):
            continue

        snaktype = str(
            mainsnak.get(
                "snaktype",
                ""
            )
        )

        if snaktype != "value":
            continue

        datavalue = mainsnak.get(
            "datavalue"
        )

        if not isinstance(
            datavalue,
            dict
        ):
            continue

        date_string, precision = (
            parse_wikidata_time(
                datavalue.get(
                    "value"
                )
            )
        )

        if not date_string:
            continue

        results.append(
            {
                "claim_number": index,
                "date": date_string,
                "precision": precision,
                "precision_name": precision_name(
                    precision
                ),
                "rank": rank,
            }
        )

    return results


def extract_entity_result(
    entity: dict[str, Any]
) -> dict[str, Any]:

    qid = str(
        entity.get(
            "id",
            ""
        )
    )

    if not qid:

        raise RuntimeError(
            "Wikidata returned an entity "
            "without an ID."
        )

    # --------------------------------------------------------
    # Explicitly missing Wikidata entity.
    # --------------------------------------------------------

    if entity.get(
        "missing"
    ) is not None:

        return {
            "qid": qid,
            "entity_status": "missing",
            "has_entity": False,
            "p569_claims": [],
            "p569_count": 0,
        }

    p569_claims = (
        extract_p569_claims(
            entity
        )
    )

    return {
        "qid": qid,
        "entity_status": "found",
        "has_entity": True,
        "p569_claims": p569_claims,
        "p569_count": len(
            p569_claims
        ),
    }


# ============================================================
# AUDIT ONE BATCH
# ============================================================

def audit_batch(
    qids: list[str]
) -> dict[str, dict[str, Any]]:

    last_error = None

    for attempt in range(
        MAX_RETRIES + 1
    ):

        try:

            data = request_wikidata_batch(
                qids
            )

            entities = data.get(
                "entities"
            )

            results = {}

            for entity in entities:

                if not isinstance(
                    entity,
                    dict
                ):
                    continue

                result = (
                    extract_entity_result(
                        entity
                    )
                )

                results[
                    result["qid"]
                ] = result

            # Final safety check.
            if set(
                results.keys()
            ) != set(
                qids
            ):

                missing = (
                    set(qids)
                    - set(results.keys())
                )

                stats[
                    "incomplete_responses"
                ] += 1

                raise TemporaryWikidataError(
                    "Final batch completeness "
                    "check failed. Missing "
                    f"{len(missing)} QIDs.",
                    wait_seconds=None
                )

            return results

        except TemporaryWikidataError as exc:

            last_error = exc

            if attempt >= MAX_RETRIES:
                break

            stats[
                "retries"
            ] += 1

            if (
                exc.wait_seconds
                is not None
            ):

                wait_seconds = max(
                    exc.wait_seconds,
                    60
                )

            else:

                index = min(
                    attempt,
                    len(
                        MAXLAG_WAIT_SCHEDULE
                    ) - 1
                )

                wait_seconds = (
                    MAXLAG_WAIT_SCHEDULE[
                        index
                    ]
                )

            print()
            print(
                "  Temporary/incomplete response: "
                f"{exc}"
            )

            print(
                f"  Waiting {wait_seconds} "
                "seconds before retry "
                f"{attempt + 1}/"
                f"{MAX_RETRIES}..."
            )

            time.sleep(
                wait_seconds
            )

        except RuntimeError as exc:

            last_error = exc

            print()
            print(
                "  ERROR:"
            )

            print(
                f"  {exc}"
            )

            break

    raise RuntimeError(
        str(last_error)
        if last_error
        else "Unknown Wikidata error."
    )


# ============================================================
# SUMMARY
# ============================================================

def summarize_results(
    results: dict[str, Any]
) -> dict[str, Any]:

    summary = {
        "entities_found": 0,
        "confirmed_missing_entities": 0,
        "no_p569": 0,
        "single_p569": 0,
        "multiple_p569": 0,
        "day_precision": 0,
        "month_precision": 0,
        "year_precision": 0,
        "other_precision": 0,
        "preferred_claims": 0,
        "normal_claims": 0,
        "deprecated_claims": 0,
    }

    for result in results.values():

        if not isinstance(
            result,
            dict
        ):
            continue

        if (
            result.get(
                "entity_status"
            )
            == "missing"
        ):

            summary[
                "confirmed_missing_entities"
            ] += 1

            continue

        if (
            result.get(
                "entity_status"
            )
            != "found"
        ):

            continue

        summary[
            "entities_found"
        ] += 1

        claims = result.get(
            "p569_claims",
            []
        )

        if not claims:

            summary[
                "no_p569"
            ] += 1

            continue

        if len(
            claims
        ) == 1:

            summary[
                "single_p569"
            ] += 1

        else:

            summary[
                "multiple_p569"
            ] += 1

        for claim in claims:

            precision = claim.get(
                "precision_name"
            )

            if precision == "day":

                summary[
                    "day_precision"
                ] += 1

            elif precision == "month":

                summary[
                    "month_precision"
                ] += 1

            elif precision == "year":

                summary[
                    "year_precision"
                ] += 1

            else:

                summary[
                    "other_precision"
                ] += 1

            rank = claim.get(
                "rank"
            )

            if rank == "preferred":

                summary[
                    "preferred_claims"
                ] += 1

            elif rank == "normal":

                summary[
                    "normal_claims"
                ] += 1

            elif rank == "deprecated":

                summary[
                    "deprecated_claims"
                ] += 1

    return summary


# ============================================================
# CSV OUTPUT
# ============================================================

def write_csv(
    reep_records: list[dict[str, str]],
    results: dict[str, Any]
) -> None:

    fieldnames = [
        "reep_id",
        "label",
        "qid",
        "entity_status",
        "has_entity",
        "p569_count",
        "dob_dates",
        "dob_precisions",
        "dob_ranks",
    ]

    with open(
        CSV_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for record in reep_records:

            qid = record[
                "qid"
            ]

            result = results.get(
                qid
            )

            if not isinstance(
                result,
                dict
            ):
                continue

            claims = result.get(
                "p569_claims",
                []
            )

            writer.writerow(
                {
                    "reep_id": record[
                        "reep_id"
                    ],
                    "label": record[
                        "label"
                    ],
                    "qid": qid,
                    "entity_status": result.get(
                        "entity_status",
                        ""
                    ),
                    "has_entity": result.get(
                        "has_entity",
                        False
                    ),
                    "p569_count": len(
                        claims
                    ),
                    "dob_dates": ";".join(
                        str(
                            claim.get(
                                "date",
                                ""
                            )
                        )
                        for claim in claims
                    ),
                    "dob_precisions": ";".join(
                        str(
                            claim.get(
                                "precision_name",
                                ""
                            )
                        )
                        for claim in claims
                    ),
                    "dob_ranks": ";".join(
                        str(
                            claim.get(
                                "rank",
                                ""
                            )
                        )
                        for claim in claims
                    ),
                }
            )


# ============================================================
# JSON OUTPUT
# ============================================================

def write_json(
    reep_records: list[dict[str, str]],
    results: dict[str, Any],
    completed_batches: set[int],
    total_batches: int
) -> None:

    summary = summarize_results(
        results
    )

    unique_qids = {
        record["qid"]
        for record in reep_records
    }

    output = {
        "generated_at": now_utc(),
        "source_database": SOURCE_DB,
        "read_only": True,
        "total_reep_rows": len(
            reep_records
        ),
        "unique_qids": len(
            unique_qids
        ),
        "total_batches": total_batches,
        "batches_completed": len(
            completed_batches
        ),
        "qids_successfully_audited": len(
            results
        ),
        "qids_not_yet_audited": (
            len(unique_qids)
            - len(results)
        ),
        "summary": summary,
        "run_statistics": stats,
        "note": (
            "P569 claims are copied from Wikidata. "
            "Multiple claims are preserved and are "
            "not automatically reduced to one DOB."
        ),
    }

    atomic_write_json(
        JSON_FILE,
        output
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    ensure_output_dir()

    print()
    print(
        "REEP → WIKIDATA DOB BULK AUDIT"
    )

    print(
        "=" * 70
    )

    print()

    print(
        "READ-ONLY — source REEP database "
        "will NOT be modified."
    )

    print()

    # --------------------------------------------------------
    # Load REEP QIDs
    # --------------------------------------------------------

    reep_records = load_reep_qids()

    unique_qids = sorted(
        {
            record["qid"]
            for record in reep_records
        }
    )

    print(
        f"Confirmed REEP player rows: "
        f"{len(reep_records):,}"
    )

    print(
        f"Unique Wikidata QIDs: "
        f"{len(unique_qids):,}"
    )

    # --------------------------------------------------------
    # Fixed batches
    # --------------------------------------------------------

    batches = make_batches(
        unique_qids
    )

    total_batches = len(
        batches
    )

    print()

    # --------------------------------------------------------
    # Load progress
    # --------------------------------------------------------

    progress = load_progress()

    completed_batches = (
        get_completed_batches(
            progress
        )
    )

    results = progress.get(
        "results",
        {}
    )

    if not isinstance(
        results,
        dict
    ):

        raise RuntimeError(
            "Progress results are not a dictionary."
        )

    # --------------------------------------------------------
    # Validate batch numbers
    # --------------------------------------------------------

    invalid_batches = {
        number
        for number in completed_batches
        if number < 1
        or number > total_batches
    }

    if invalid_batches:

        print(
            "WARNING: Ignoring invalid "
            "completed batch numbers:"
        )

        print(
            sorted(
                invalid_batches
            )
        )

        completed_batches -= (
            invalid_batches
        )

    # --------------------------------------------------------
    # Save migrated progress format
    # --------------------------------------------------------

    progress["results"] = (
        results
    )

    save_progress(
        progress,
        completed_batches
    )

    print(
        f"Total batches: "
        f"{total_batches:,}"
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

    # --------------------------------------------------------
    # Process remaining batches
    # --------------------------------------------------------

    for batch_number, batch_qids in enumerate(
        batches,
        start=1
    ):

        if batch_number in completed_batches:
            continue

        print(
            f"Batch {batch_number}/"
            f"{total_batches} "
            f"({len(batch_qids)} QIDs)..."
        )

        try:

            batch_results = audit_batch(
                batch_qids
            )

        except Exception as exc:

            print()
            print(
                "  ERROR:"
            )

            print(
                f"  {exc}"
            )

            print()

            print(
                "  This batch was NOT "
                "marked complete."
            )

            print(
                "  It will be retried "
                "on the next run."
            )

            print()

            print(
                "Stopping audit safely."
            )

            break

        # ----------------------------------------------------
        # Only successful complete batches reach here.
        # ----------------------------------------------------

        results.update(
            batch_results
        )

        completed_batches.add(
            batch_number
        )

        progress["results"] = (
            results
        )

        save_progress(
            progress,
            completed_batches
        )

        stats[
            "completed_batches_this_run"
        ] += 1

        print(
            "  Completed and progress saved."
        )

        # ----------------------------------------------------
        # Deliberate pause after success.
        # ----------------------------------------------------

        if batch_number < total_batches:

            print(
                f"  Waiting "
                f"{SUCCESS_DELAY_SECONDS} "
                "seconds before next batch..."
            )

            time.sleep(
                SUCCESS_DELAY_SECONDS
            )

    # --------------------------------------------------------
    # Write current outputs.
    # --------------------------------------------------------

    write_csv(
        reep_records,
        results
    )

    write_json(
        reep_records,
        results,
        completed_batches,
        total_batches
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    summary = summarize_results(
        results
    )

    unique_qid_count = len(
        unique_qids
    )

    audited_count = len(
        results
    )

    not_audited = max(
        unique_qid_count
        - audited_count,
        0
    )

    print()

    print(
        "=" * 70
    )

    print(
        "WIKIDATA DOB BULK AUDIT SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        f"Total unique QIDs:          "
        f"{unique_qid_count:,}"
    )

    print(
        f"Batches completed:          "
        f"{len(completed_batches):,} / "
        f"{total_batches:,}"
    )

    print(
        f"QIDs successfully audited:  "
        f"{audited_count:,}"
    )

    print(
        f"QIDs not yet audited:       "
        f"{not_audited:,}"
    )

    print(
        f"Entities found:             "
        f"{summary['entities_found']:,}"
    )

    print(
        f"Confirmed missing entities: "
        f"{summary['confirmed_missing_entities']:,}"
    )

    print(
        f"No P569:                    "
        f"{summary['no_p569']:,}"
    )

    print(
        f"Single P569:                "
        f"{summary['single_p569']:,}"
    )

    print(
        f"Multiple P569:              "
        f"{summary['multiple_p569']:,}"
    )

    print(
        f"Day precision:              "
        f"{summary['day_precision']:,}"
    )

    print(
        f"Month precision:            "
        f"{summary['month_precision']:,}"
    )

    print(
        f"Year precision:             "
        f"{summary['year_precision']:,}"
    )

    print(
        f"Other precision:            "
        f"{summary['other_precision']:,}"
    )

    print(
        f"Preferred claims:           "
        f"{summary['preferred_claims']:,}"
    )

    print(
        f"Normal claims:              "
        f"{summary['normal_claims']:,}"
    )

    print(
        f"Deprecated claims:          "
        f"{summary['deprecated_claims']:,}"
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
        f"Maxlag events:              "
        f"{stats['maxlag_events']:,}"
    )

    print(
        f"HTTP 429 events:            "
        f"{stats['http_429_events']:,}"
    )

    print(
        f"HTTP 5xx events:            "
        f"{stats['http_5xx_events']:,}"
    )

    print(
        f"Timeout errors:             "
        f"{stats['timeout_errors']:,}"
    )

    print(
        f"Connection errors:          "
        f"{stats['connection_errors']:,}"
    )

    print(
        f"Incomplete responses:       "
        f"{stats['incomplete_responses']:,}"
    )

    print()

    print(
        f"CSV output:  {CSV_FILE}"
    )

    print(
        f"JSON output: {JSON_FILE}"
    )

    print(
        f"Progress:    {PROGRESS_FILE}"
    )

    print()

    print(
        "No REEP database changes were made."
    )

    print(
        "=" * 70
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()