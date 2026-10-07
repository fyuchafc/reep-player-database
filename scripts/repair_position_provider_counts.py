import duckdb
import json
from pathlib import Path


DB_PATH = "output/reep-player-position-evidence.duckdb"

REPORT_PATH = (
    "output/reep-player-position-provider-count-repair.json"
)


def main():

    print("=" * 80)
    print("REEP V1.1 POSITION PROVIDER COUNT REPAIR")
    print("=" * 80)
    print()

    print("Database:")
    print(DB_PATH)
    print()

    con = duckdb.connect(DB_PATH)

    # ------------------------------------------------------------
    # Check current state
    # ------------------------------------------------------------

    before = con.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN position_status = 'supported'
                    THEN 1
                    ELSE 0
                END
            ) AS supported,
            SUM(
                CASE
                    WHEN position_status = 'no_position'
                    THEN 1
                    ELSE 0
                END
            ) AS no_position,
            SUM(
                CASE
                    WHEN provider_count <> (
                        SELECT COUNT(DISTINCT c.provider)
                        FROM player_position_claims c
                        WHERE c.reep_id = p.reep_id
                    )
                    THEN 1
                    ELSE 0
                END
            ) AS mismatches
        FROM player_position p
    """).fetchone()

    print("BEFORE REPAIR")
    print("-" * 80)
    print(f"Total players:       {before[0]}")
    print(f"Supported players:   {before[1]}")
    print(f"No-position players: {before[2]}")
    print(f"Provider mismatches: {before[3]}")
    print()

    # ------------------------------------------------------------
    # Repair provider_count
    # ------------------------------------------------------------

    con.execute("""
        UPDATE player_position AS p
        SET provider_count = (
            SELECT COUNT(DISTINCT c.provider)
            FROM player_position_claims AS c
            WHERE c.reep_id = p.reep_id
        )
    """)

    con.commit()

    # ------------------------------------------------------------
    # Validate repair
    # ------------------------------------------------------------

    after = con.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN position_status = 'supported'
                    THEN 1
                    ELSE 0
                END
            ) AS supported,
            SUM(
                CASE
                    WHEN position_status = 'no_position'
                    THEN 1
                    ELSE 0
                END
            ) AS no_position,
            SUM(
                CASE
                    WHEN provider_count <> (
                        SELECT COUNT(DISTINCT c.provider)
                        FROM player_position_claims c
                        WHERE c.reep_id = p.reep_id
                    )
                    THEN 1
                    ELSE 0
                END
            ) AS mismatches
        FROM player_position p
    """).fetchone()

    print("AFTER REPAIR")
    print("-" * 80)
    print(f"Total players:       {after[0]}")
    print(f"Supported players:   {after[1]}")
    print(f"No-position players: {after[2]}")
    print(f"Provider mismatches: {after[3]}")
    print()

    # ------------------------------------------------------------
    # Check expected values
    # ------------------------------------------------------------

    supported_wrong = con.execute("""
        SELECT COUNT(*)
        FROM player_position
        WHERE
            position_status = 'supported'
            AND provider_count <> 1
    """).fetchone()[0]

    no_position_wrong = con.execute("""
        SELECT COUNT(*)
        FROM player_position
        WHERE
            position_status = 'no_position'
            AND provider_count <> 0
    """).fetchone()[0]

    status = (
        "PASS"
        if (
            after[3] == 0
            and supported_wrong == 0
            and no_position_wrong == 0
        )
        else "FAIL"
    )

    report = {
        "database": DB_PATH,
        "before_provider_mismatches": before[3],
        "after_provider_mismatches": after[3],
        "supported_players": after[1],
        "no_position_players": after[2],
        "supported_wrong_provider_count": supported_wrong,
        "no_position_wrong_provider_count": no_position_wrong,
        "status": status,
    }

    Path(
        REPORT_PATH
    ).write_text(
        json.dumps(
            report,
            indent=2
        ),
        encoding="utf-8"
    )

    print("=" * 80)
    print("REPAIR RESULT")
    print("=" * 80)

    print(
        f"Supported rows with wrong provider_count: "
        f"{supported_wrong}"
    )

    print(
        f"No-position rows with wrong provider_count: "
        f"{no_position_wrong}"
    )

    print(
        f"Remaining provider mismatches: "
        f"{after[3]}"
    )

    print()

    print(
        f"STATUS: {status}"
    )

    print()

    print(
        f"Repair report: {REPORT_PATH}"
    )

    print("=" * 80)

    con.close()


if __name__ == "__main__":
    main()