import sys
import random
from datetime import datetime, timezone

import duckdb

# ================================================================
# CONFIGURATION
# ================================================================

OUTPUT_DB = "output/reep-player-position-evidence.duckdb"

PROVIDER = "transfermarkt"
NAMESPACE = "spieler"
PARSER_VERSION = "TM-position-parser-v4"

MIN_DELAY = 55
MAX_DELAY = 75

VALID_POSITIONS = {
    "Goalkeeper",
    "Centre-Back",
    "Left-Back",
    "Right-Back",
    "Defensive Midfield",
    "Central Midfield",
    "Left Midfield",
    "Right Midfield",
    "Attacking Midfield",
    "Left Winger",
    "Right Winger",
    "Second Striker",
    "Centre-Forward",
}

# ================================================================
# IMPORT PRODUCTION FETCH/PARSER FUNCTIONS
# ================================================================

sys.path.insert(0, "scripts")

from build_position_enrichment_batch import (
    fetch_html,
    extract_positions,
    normalize_position,
)

# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 80)
    print("REEP V1.1 FAILED POSITION FETCH RETRY")
    print("=" * 80)
    print()

    print("OUTPUT DATABASE:")
    print(OUTPUT_DB)

    print()
    print("MODE: TARGETED RETRY ONLY")
    print()

    con = duckdb.connect(OUTPUT_DB)

    # ------------------------------------------------------------
    # Find only failed fetches
    # ------------------------------------------------------------

    failed = con.execute("""
        SELECT
            reep_id,
            label,
            provider,
            provider_id,
            source_url
        FROM position_fetch_log
        WHERE fetch_status = 'fetch_failed'
        ORDER BY reep_id
    """).fetchall()

    print(
        f"Failed fetches found: {len(failed)}"
    )

    print()

    if not failed:

        print("No failed fetches require retry.")

        con.close()

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
    claims_created = 0

    # ------------------------------------------------------------
    # Process only failed rows
    # ------------------------------------------------------------

    for index, (
        reep_id,
        label,
        provider,
        transfermarkt_id,
        source_url
    ) in enumerate(
        failed,
        start=1
    ):

        print(
            f"[{index}/{len(failed)}] {label}"
        )

        print(
            f"      REEP ID: {reep_id}"
        )

        print(
            f"      TM ID: {transfermarkt_id}"
        )

        print(
            f"      URL: {source_url}"
        )

        fetched = fetch_html(source_url)

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

                con.execute("""
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
                    source_url,
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

                con.execute("""
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
                    source_url,
                    200,
                    PARSER_VERSION,
                    now
                ])

                current_claim_count += 1

            claims_created += current_claim_count

            # ----------------------------------------------------
            # Canonical position
            # ----------------------------------------------------

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

            provider_count = (
                1
                if current_claim_count > 0
                else 0
            )

            # ----------------------------------------------------
            # Replace canonical position row
            # ----------------------------------------------------

            con.execute("""
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

            print(
                f"      HTTP 200 "
                f"({fetched['bytes']} bytes)"
            )

            if primary_position:

                print(
                    f"      Main: {primary_position}"
                )

            else:

                print(
                    "      Position: NOT FOUND"
                )

            if secondary_positions:

                print(
                    f"      Other: {secondary_positions}"
                )

            print(
                f"      Claims: {current_claim_count}"
            )

            fetch_status = "success"

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
        # Replace fetch log
        # --------------------------------------------------------

        con.execute("""
            INSERT OR REPLACE INTO position_fetch_log
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            reep_id,
            label,
            PROVIDER,
            transfermarkt_id,
            source_url,
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

        con.commit()

        # --------------------------------------------------------
        # Delay
        # --------------------------------------------------------

        if index < len(failed):

            wait = random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )

            print(
                f"      Waiting {wait:.1f} seconds..."
            )

            import time

            time.sleep(wait)

        print()

    # ============================================================
    # SUMMARY
    # ============================================================

    print("=" * 80)
    print("RETRY RESULT")
    print("=" * 80)

    print()

    print(
        f"Players retried: {len(failed)}"
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
        f"Supported positions: {supported}"
    )

    print(
        f"No position found: {no_position}"
    )

    print(
        f"Position claims created: {claims_created}"
    )

    print()

    if http_200 == len(failed):

        print("STATUS: PASS")

    else:

        print(
            "STATUS: REVIEW REQUIRED"
        )

    print()

    con.close()


if __name__ == "__main__":
    main()