import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
import duckdb

from pathlib import Path
from datetime import datetime, timezone


# ================================================================
# CONFIGURATION
# ================================================================

SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DB = "output/reep-player-position-evidence.duckdb"

OUTPUT_REPORT = (
    "output/reep-player-position-enrichment-batch-report.json"
)

DEFAULT_BATCH_SIZE = 250

MIN_DELAY = 10
MAX_DELAY = 15

MAX_RETRIES = 3

PROVIDER = "transfermarkt"
NAMESPACE = "spieler"

PARSER_VERSION = "transfermarkt-position-parser-v4"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)


# ================================================================
# POSITION VOCABULARY
# ================================================================

VALID_POSITIONS = {
    "Goalkeeper",
    "Centre-Back",
    "Left-Back",
    "Right-Back",
    "Defensive Midfield",
    "Central Midfield",
    "Attacking Midfield",
    "Left Midfield",
    "Right Midfield",
    "Left Winger",
    "Right Winger",
    "Second Striker",
    "Centre-Forward",
}


def normalize_position(position):

    mapping = {
        "Goalkeeper": "Goalkeeper",
        "Centre-Back": "Centre-Back",
        "Left-Back": "Left-Back",
        "Right-Back": "Right-Back",
        "Defensive Midfield": "Defensive Midfield",
        "Central Midfield": "Central Midfield",
        "Attacking Midfield": "Attacking Midfield",
        "Left Midfield": "Left Midfield",
        "Right Midfield": "Right Midfield",
        "Left Winger": "Left Winger",
        "Right Winger": "Right Winger",
        "Second Striker": "Second Striker",
        "Centre-Forward": "Centre-Forward",
    }

    return mapping.get(position, position)


def clean_text(value):

    if not value:
        return ""

    value = re.sub(r"\s+", " ", value)

    return value.strip()


# ================================================================
# DATABASE INITIALIZATION
# ================================================================

def initialize_database(con):

    con.execute("""
        CREATE TABLE IF NOT EXISTS player_position_claims (
            reep_id VARCHAR NOT NULL,
            label VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            provider_namespace VARCHAR NOT NULL,
            provider_id VARCHAR NOT NULL,
            position VARCHAR NOT NULL,
            position_normalized VARCHAR NOT NULL,
            position_type VARCHAR NOT NULL,
            source_url VARCHAR NOT NULL,
            http_status INTEGER,
            parser_version VARCHAR NOT NULL,
            retrieved_at VARCHAR NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS player_position (
            reep_id VARCHAR PRIMARY KEY,
            label VARCHAR NOT NULL,
            primary_position VARCHAR,
            secondary_positions VARCHAR,
            position_status VARCHAR NOT NULL,
            evidence_count INTEGER NOT NULL,
            provider_count INTEGER NOT NULL,
            source VARCHAR NOT NULL,
            updated_at VARCHAR NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS position_fetch_log (
            reep_id VARCHAR PRIMARY KEY,
            label VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            provider_id VARCHAR NOT NULL,
            source_url VARCHAR NOT NULL,
            http_status INTEGER,
            fetch_status VARCHAR NOT NULL,
            attempts INTEGER NOT NULL,
            bytes_received INTEGER NOT NULL,
            error VARCHAR,
            fetched_at VARCHAR NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE IF NOT EXISTS database_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR
        )
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_position_claims_reep_id
        ON player_position_claims(reep_id)
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_position_claims_provider_id
        ON player_position_claims(
            provider,
            provider_namespace,
            provider_id
        )
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_player_position_primary
        ON player_position(primary_position)
    """)

    con.execute("""
        CREATE INDEX IF NOT EXISTS
        idx_position_fetch_status
        ON position_fetch_log(fetch_status)
    """)


# ================================================================
# FETCH
# ================================================================

def fetch_html(url):

    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,image/avif,"
                        "image/webp,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                status = response.getcode()

                raw = response.read()

                if raw[:2] == b"\x1f\x8b":

                    import gzip

                    raw = gzip.decompress(raw)

                html = raw.decode(
                    "utf-8",
                    errors="replace"
                )

                return {
                    "status": status,
                    "html": html,
                    "bytes": len(raw),
                    "attempts": attempt,
                    "error": "",
                }

        except urllib.error.HTTPError as e:

            last_error = (
                f"HTTPError: HTTP Error "
                f"{e.code}: {e.reason}"
            )

            if attempt < MAX_RETRIES:

                if e.code == 403:
                    wait = 20 * attempt

                elif e.code == 429:
                    wait = 30 * attempt

                else:
                    wait = 10 * attempt

                print(
                    f"      HTTP {e.code}. "
                    f"Retrying after {wait}s..."
                )

                time.sleep(wait)

        except Exception as e:

            last_error = (
                f"{type(e).__name__}: {str(e)}"
            )

            if attempt < MAX_RETRIES:

                wait = 10 * attempt

                print(
                    f"      {type(e).__name__}. "
                    f"Retrying after {wait}s..."
                )

                time.sleep(wait)

    return {
        "status": None,
        "html": "",
        "bytes": 0,
        "attempts": MAX_RETRIES,
        "error": last_error,
    }


# ================================================================
# EXACT TRANSFERMARKT POSITION PARSER
# ================================================================

def extract_positions(html):

    main_positions = []
    other_positions = []

    pattern = re.compile(
        r'<dt[^>]*class=["\'][^"\']*detail-position__title'
        r'[^"\']*["\'][^>]*>\s*'
        r'(Main position|Other position)\s*:?\s*'
        r'</dt>'
        r'(?P<body>.*?)'
        r'(?=<dt[^>]*class=["\']'
        r'[^"\']*detail-position__title'
        r'[^"\']*["\']|</dl>|</div>\s*</div>\s*</div>)',
        re.IGNORECASE | re.DOTALL
    )

    for match in pattern.finditer(html):

        label = clean_text(
            match.group(1)
        )

        body = match.group("body")

        values = re.findall(
            r'<dd[^>]*class=["\']'
            r'[^"\']*detail-position__position'
            r'[^"\']*["\'][^>]*>\s*'
            r'(.*?)\s*</dd>',
            body,
            re.IGNORECASE | re.DOTALL
        )

        cleaned_values = []

        for value in values:

            value = re.sub(
                r"<[^>]+>",
                " ",
                value
            )

            value = clean_text(value)

            if (
                value
                and value not in cleaned_values
            ):
                cleaned_values.append(value)

        if label.lower() == "main position":
            main_positions.extend(cleaned_values)

        elif label.lower() == "other position":
            other_positions.extend(cleaned_values)

    main_positions = list(
        dict.fromkeys(main_positions)
    )

    other_positions = list(
        dict.fromkeys(other_positions)
    )

    return main_positions, other_positions


# ================================================================
# READ REEP TRANSFERMARKT IDs
# ================================================================

def load_candidates(source_con):

    return source_con.execute("""
        SELECT DISTINCT
            b.reep_id,
            p.label,
            b.external_id AS transfermarkt_id
        FROM bridges b
        INNER JOIN players p
            ON b.reep_id = p.reep_id
        WHERE
            LOWER(TRIM(b.provider)) = 'transfermarkt'
            AND LOWER(TRIM(b.namespace)) = 'spieler'
            AND b.external_id IS NOT NULL
            AND TRIM(b.external_id) <> ''
        ORDER BY b.reep_id
    """).fetchall()


# ================================================================
# BATCH SIZE
# ================================================================

def get_batch_size():

    if len(sys.argv) == 1:
        return DEFAULT_BATCH_SIZE

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "  python "
            "scripts\\build_position_enrichment_batch.py "
            "[batch_size]"
        )

        sys.exit(1)

    try:

        batch_size = int(
            sys.argv[1]
        )

    except ValueError:

        print(
            "ERROR: Batch size must be a whole number."
        )

        sys.exit(1)

    if batch_size < 1:

        print(
            "ERROR: Batch size must be at least 1."
        )

        sys.exit(1)

    return batch_size


# ================================================================
# MAIN
# ================================================================

def main():

    batch_size = get_batch_size()

    print("=" * 80)
    print("REEP V1.1 POSITION ENRICHMENT")
    print("=" * 80)
    print()

    print(
        f"Requested batch size: {batch_size}"
    )

    print(
        f"Delay between requests: "
        f"{MIN_DELAY}-{MAX_DELAY} seconds"
    )

    print()

    print("SOURCE DATABASE:")
    print(SOURCE_DB)

    print()

    print("SOURCE MODE: READ-ONLY")

    print()

    print("OUTPUT DATABASE:")
    print(OUTPUT_DB)

    print()

    source_con = duckdb.connect(
        SOURCE_DB,
        read_only=True
    )

    print(
        "Source database opened READ-ONLY."
    )

    output_con = duckdb.connect(
        OUTPUT_DB
    )

    initialize_database(
        output_con
    )

    # ------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------

    metadata = {
        "database_type":
            "REEP v1.1 position evidence",
        "provider":
            PROVIDER,
        "provider_namespace":
            NAMESPACE,
        "parser_version":
            PARSER_VERSION,
        "source_database":
            SOURCE_DB,
        "last_requested_batch_size":
            str(batch_size),
        "minimum_delay_seconds":
            str(MIN_DELAY),
        "maximum_delay_seconds":
            str(MAX_DELAY),
    }

    for key, value in metadata.items():

        output_con.execute("""
            INSERT OR REPLACE INTO
            database_metadata
            VALUES (?, ?)
        """, [
            key,
            value
        ])

    # ------------------------------------------------------------
    # Candidates
    # ------------------------------------------------------------

    candidates = load_candidates(
        source_con
    )

    print(
        f"Transfermarkt-linked REEP players: "
        f"{len(candidates)}"
    )

    processed = {
        row[0]
        for row in output_con.execute("""
            SELECT reep_id
            FROM position_fetch_log
            WHERE fetch_status = 'success'
        """).fetchall()
    }

    remaining = [
        row
        for row in candidates
        if row[0] not in processed
    ]

    print(
        f"Successfully processed previously: "
        f"{len(processed)}"
    )

    print(
        f"Remaining candidates: "
        f"{len(remaining)}"
    )

    batch = remaining[:batch_size]

    print(
        f"Players selected for this run: "
        f"{len(batch)}"
    )

    print()

    if not batch:

        print(
            "No remaining players require processing."
        )

        source_con.close()
        output_con.close()

        return

    # ------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------

    http_200 = 0
    http_403 = 0
    http_429 = 0
    other_failures = 0

    supported = 0
    no_position = 0
    claim_count = 0

    # ------------------------------------------------------------
    # Process
    # ------------------------------------------------------------

    for index, (
        reep_id,
        label,
        transfermarkt_id
    ) in enumerate(
        batch,
        start=1
    ):

        url = (
            "https://www.transfermarkt.com/"
            f"spieler/profil/spieler/"
            f"{transfermarkt_id}"
        )

        print(
            f"[{index}/{len(batch)}] {label}"
        )

        print(
            f"      REEP ID: {reep_id}"
        )

        print(
            f"      TM ID: {transfermarkt_id}"
        )

        fetched = fetch_html(url)

        status = fetched["status"]

        now = datetime.now(
            timezone.utc
        ).isoformat()

        if status == 200:

            http_200 += 1

            main_positions, other_positions = (
                extract_positions(
                    fetched["html"]
                )
            )

            current_claim_count = 0

            # ----------------------------------------------------
            # Main position claims
            # ----------------------------------------------------

            for position in main_positions:

                normalized = normalize_position(
                    position
                )

                if normalized not in VALID_POSITIONS:
                    continue

                output_con.execute("""
                    INSERT INTO player_position_claims
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    reep_id,
                    label,
                    PROVIDER,
                    NAMESPACE,
                    transfermarkt_id,
                    position,
                    normalized,
                    "main",
                    url,
                    200,
                    PARSER_VERSION,
                    now
                ])

                current_claim_count += 1

            # ----------------------------------------------------
            # Other position claims
            # ----------------------------------------------------

            for position in other_positions:

                normalized = normalize_position(
                    position
                )

                if normalized not in VALID_POSITIONS:
                    continue

                output_con.execute("""
                    INSERT INTO player_position_claims
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    reep_id,
                    label,
                    PROVIDER,
                    NAMESPACE,
                    transfermarkt_id,
                    position,
                    normalized,
                    "other",
                    url,
                    200,
                    PARSER_VERSION,
                    now
                ])

                current_claim_count += 1

            claim_count += current_claim_count

            normalized_main = [
                normalize_position(x)
                for x in main_positions
                if normalize_position(x)
                in VALID_POSITIONS
            ]

            normalized_other = [
                normalize_position(x)
                for x in other_positions
                if normalize_position(x)
                in VALID_POSITIONS
            ]

            primary_position = (
                normalized_main[0]
                if normalized_main
                else None
            )

            secondary = []

            for position in normalized_other:

                if (
                    position != primary_position
                    and position not in secondary
                ):
                    secondary.append(position)

            secondary_positions = (
                " | ".join(secondary)
                if secondary
                else None
            )

            if primary_position:

                position_status = "supported"

                supported += 1

            else:

                position_status = "no_position"

                no_position += 1

            # IMPORTANT:
            # Provider count is based on actual claims.
            provider_count = (
                1
                if current_claim_count > 0
                else 0
            )

            output_con.execute("""
                INSERT OR REPLACE INTO player_position
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                reep_id,
                label,
                primary_position,
                secondary_positions,
                position_status,
                current_claim_count,
                provider_count,
                PROVIDER,
                now
            ])

            fetch_status = "success"

            print(
                f"      HTTP 200 "
                f"({fetched['bytes']} bytes)"
            )

            if primary_position:

                print(
                    f"      Main: "
                    f"{primary_position}"
                )

            if secondary_positions:

                print(
                    f"      Other: "
                    f"{secondary_positions}"
                )

            if not primary_position:

                print(
                    "      Position: NOT FOUND"
                )

        else:

            if status == 403:
                http_403 += 1

            elif status == 429:
                http_429 += 1

            else:
                other_failures += 1

            fetch_status = "fetch_failed"

            print(
                f"      FETCH FAILURE: "
                f"HTTP {status} | "
                f"{fetched['error']}"
            )

        # --------------------------------------------------------
        # Fetch log
        # --------------------------------------------------------

        output_con.execute("""
            INSERT OR REPLACE INTO position_fetch_log
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            reep_id,
            label,
            PROVIDER,
            transfermarkt_id,
            url,
            status,
            fetch_status,
            fetched["attempts"],
            fetched["bytes"],
            fetched["error"],
            now
        ])

        # --------------------------------------------------------
        # Commit after every player
        # --------------------------------------------------------

        output_con.commit()

        # --------------------------------------------------------
        # Delay
        # --------------------------------------------------------

        if index < len(batch):

            wait = random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )

            print(
                f"      Waiting "
                f"{wait:.1f}s..."
            )

            time.sleep(wait)

        print()

    # ------------------------------------------------------------
    # Report
    # ------------------------------------------------------------

    total = len(batch)

    http_success_rate = (
        http_200 / total * 100
        if total
        else 0
    )

    position_rate = (
        supported / http_200 * 100
        if http_200
        else 0
    )

    report = {
        "batch_size_requested": batch_size,
        "batch_size_processed": total,
        "http_200": http_200,
        "http_403": http_403,
        "http_429": http_429,
        "other_failures": other_failures,
        "http_200_rate_percent": round(
            http_success_rate,
            2
        ),
        "supported_players": supported,
        "no_position_players": no_position,
        "position_found_rate_of_successful_pages":
            round(position_rate, 2),
        "position_claims_created": claim_count,
        "database": OUTPUT_DB,
        "parser_version": PARSER_VERSION,
        "provider": PROVIDER,
        "provider_namespace": NAMESPACE,
        "status": (
            "PASS"
            if (
                http_200 == total
                and http_403 == 0
                and http_429 == 0
                and other_failures == 0
            )
            else "REVIEW REQUIRED"
        ),
    }

    Path(
        OUTPUT_REPORT
    ).write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    source_con.close()
    output_con.close()

    print("=" * 80)
    print("POSITION ENRICHMENT BATCH RESULT")
    print("=" * 80)

    print(
        f"Players processed: {total}"
    )

    print(
        f"HTTP 200: {http_200}"
    )

    print(
        f"HTTP 403: {http_403}"
    )

    print(
        f"HTTP 429: {http_429}"
    )

    print(
        f"Other failures: {other_failures}"
    )

    print(
        f"HTTP 200 rate: "
        f"{http_success_rate:.2f}%"
    )

    print(
        f"Supported positions: "
        f"{supported}"
    )

    print(
        f"No position found: "
        f"{no_position}"
    )

    print(
        f"Position claims created: "
        f"{claim_count}"
    )

    if http_200:

        print(
            f"Position found among successful pages: "
            f"{position_rate:.2f}%"
        )

    print()

    print(
        "STATUS: "
        + report["status"]
    )

    print()

    print(
        f"Database: {OUTPUT_DB}"
    )

    print(
        f"Report: {OUTPUT_REPORT}"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()