import json
import duckdb
from pathlib import Path

DB_PATH = "output/reep-player-position-evidence-test.duckdb"
OUTPUT_JSON = "output/reep-player-position-evidence-test-audit.json"

VALID_POSITION_TYPES = {
    "main",
    "other",
}

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


def main():

    print("=" * 80)
    print("REEP POSITION EVIDENCE TEST DATABASE AUDIT")
    print("=" * 80)
    print()

    print("READ-ONLY AUDIT")
    print()

    print(
        f"Database: {DB_PATH}"
    )

    print()

    con = duckdb.connect(
        DB_PATH,
        read_only=True
    )

    # ---------------------------------------------------------------
    # Required tables
    # ---------------------------------------------------------------

    tables = {
        row[0]
        for row in con.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
        """).fetchall()
    }

    required_tables = {
        "player_position_claims",
        "player_position",
        "database_metadata",
    }

    missing_tables = sorted(
        required_tables - tables
    )

    print("REQUIRED TABLES")
    print("-" * 80)

    for table in sorted(required_tables):

        if table in tables:
            print(
                f"{table}: FOUND"
            )
        else:
            print(
                f"{table}: MISSING"
            )

    print()

    # ---------------------------------------------------------------
    # Counts
    # ---------------------------------------------------------------

    player_count = con.execute("""
        SELECT COUNT(*)
        FROM player_position
    """).fetchone()[0]

    claim_count = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims
    """).fetchone()[0]

    print("COUNTS")
    print("-" * 80)

    print(
        f"Canonical players: {player_count}"
    )

    print(
        f"Position claims: {claim_count}"
    )

    print()

    # ---------------------------------------------------------------
    # Duplicate canonical players
    # ---------------------------------------------------------------

    duplicate_players = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT reep_id
            FROM player_position
            GROUP BY reep_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    print(
        f"Duplicate canonical player IDs: "
        f"{duplicate_players}"
    )

    # ---------------------------------------------------------------
    # Null/empty canonical IDs
    # ---------------------------------------------------------------

    null_canonical_ids = con.execute("""
        SELECT COUNT(*)
        FROM player_position
        WHERE reep_id IS NULL
           OR TRIM(reep_id) = ''
    """).fetchone()[0]

    print(
        f"Null/empty canonical player IDs: "
        f"{null_canonical_ids}"
    )

    # ---------------------------------------------------------------
    # Null/empty claim IDs
    # ---------------------------------------------------------------

    null_claim_ids = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims
        WHERE reep_id IS NULL
           OR TRIM(reep_id) = ''
    """).fetchone()[0]

    print(
        f"Null/empty claim player IDs: "
        f"{null_claim_ids}"
    )

    # ---------------------------------------------------------------
    # Orphan claims
    # ---------------------------------------------------------------

    orphan_claims = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims c
        LEFT JOIN player_position p
            ON c.reep_id = p.reep_id
        WHERE p.reep_id IS NULL
    """).fetchone()[0]

    print(
        f"Orphan position claims: "
        f"{orphan_claims}"
    )

    # ---------------------------------------------------------------
    # Invalid position types
    # ---------------------------------------------------------------

    invalid_position_types = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims
        WHERE position_type NOT IN ('main', 'other')
    """).fetchone()[0]

    print(
        f"Invalid position types: "
        f"{invalid_position_types}"
    )

    # ---------------------------------------------------------------
    # Invalid normalized positions
    # ---------------------------------------------------------------

    rows = con.execute("""
        SELECT DISTINCT position_normalized
        FROM player_position_claims
        WHERE position_normalized IS NOT NULL
          AND TRIM(position_normalized) <> ''
    """).fetchall()

    invalid_positions = sorted(
        {
            row[0]
            for row in rows
            if row[0] not in VALID_POSITIONS
        }
    )

    invalid_position_count = len(
        invalid_positions
    )

    print(
        f"Invalid normalized position values: "
        f"{invalid_position_count}"
    )

    if invalid_positions:

        for position in invalid_positions:

            print(
                f"  INVALID: {position}"
            )

    # ---------------------------------------------------------------
    # Empty source positions
    # ---------------------------------------------------------------

    empty_source_positions = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims
        WHERE position IS NULL
           OR TRIM(position) = ''
    """).fetchone()[0]

    print(
        f"Empty source positions: "
        f"{empty_source_positions}"
    )

    # ---------------------------------------------------------------
    # Empty normalized positions
    # ---------------------------------------------------------------

    empty_normalized_positions = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims
        WHERE position_normalized IS NULL
           OR TRIM(position_normalized) = ''
    """).fetchone()[0]

    print(
        f"Empty normalized positions: "
        f"{empty_normalized_positions}"
    )

    # ---------------------------------------------------------------
    # Unsupported canonical primary positions
    # ---------------------------------------------------------------

    canonical_primary_rows = con.execute("""
        SELECT DISTINCT primary_position
        FROM player_position
        WHERE primary_position IS NOT NULL
    """).fetchall()

    invalid_primary_positions = sorted(
        {
            row[0]
            for row in canonical_primary_rows
            if row[0] not in VALID_POSITIONS
        }
    )

    print(
        f"Invalid canonical primary positions: "
        f"{len(invalid_primary_positions)}"
    )

    # ---------------------------------------------------------------
    # Supported players without claims
    # ---------------------------------------------------------------

    supported_without_claims = con.execute("""
        SELECT COUNT(*)
        FROM player_position p
        LEFT JOIN player_position_claims c
            ON p.reep_id = c.reep_id
        WHERE p.position_status = 'supported'
        GROUP BY p.reep_id
        HAVING COUNT(c.reep_id) = 0
    """).fetchall()

    supported_without_claim_count = len(
        supported_without_claims
    )

    print(
        f"Supported players without claims: "
        f"{supported_without_claim_count}"
    )

    # ---------------------------------------------------------------
    # No-position players with claims
    # ---------------------------------------------------------------

    no_position_with_claims = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT
                p.reep_id,
                COUNT(c.reep_id) AS claim_count
            FROM player_position p
            LEFT JOIN player_position_claims c
                ON p.reep_id = c.reep_id
            WHERE p.position_status = 'no_position'
            GROUP BY p.reep_id
            HAVING COUNT(c.reep_id) > 0
        )
    """).fetchone()[0]

    print(
        f"No-position players with claims: "
        f"{no_position_with_claims}"
    )

    # ---------------------------------------------------------------
    # Primary position must come from main claim
    # ---------------------------------------------------------------

    primary_without_main_claim = con.execute("""
        SELECT COUNT(*)
        FROM player_position p
        WHERE p.primary_position IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM player_position_claims c
              WHERE c.reep_id = p.reep_id
                AND c.position_type = 'main'
                AND c.position_normalized =
                    p.primary_position
          )
    """).fetchone()[0]

    print(
        f"Primary positions without matching main claims: "
        f"{primary_without_main_claim}"
    )

    # ---------------------------------------------------------------
    # Primary duplicated in secondary
    # ---------------------------------------------------------------

    primary_in_secondary = con.execute("""
        SELECT COUNT(*)
        FROM player_position p
        WHERE p.primary_position IS NOT NULL
          AND p.secondary_positions IS NOT NULL
          AND (
              '|' || p.secondary_positions || '|'
          ) LIKE
              '%|'
              || p.primary_position
              || '|%'
    """).fetchone()[0]

    print(
        f"Primary duplicated in secondary positions: "
        f"{primary_in_secondary}"
    )

    # ---------------------------------------------------------------
    # Provider consistency
    # ---------------------------------------------------------------

    invalid_providers = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims
        WHERE provider <> 'transfermarkt'
    """).fetchone()[0]

    print(
        f"Invalid providers: "
        f"{invalid_providers}"
    )

    # ---------------------------------------------------------------
    # HTTP consistency
    # ---------------------------------------------------------------

    non_200_claims = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims
        WHERE http_status <> 200
    """).fetchone()[0]

    print(
        f"Claims from non-200 pages: "
        f"{non_200_claims}"
    )

    # ---------------------------------------------------------------
    # Expected test counts
    # ---------------------------------------------------------------

    expected_players_pass = (
        player_count == 25
    )

    expected_supported_pass = (
        con.execute("""
            SELECT COUNT(*)
            FROM player_position
            WHERE position_status = 'supported'
        """).fetchone()[0] == 21
    )

    expected_no_position_pass = (
        con.execute("""
            SELECT COUNT(*)
            FROM player_position
            WHERE position_status = 'no_position'
        """).fetchone()[0] == 4
    )

    # ---------------------------------------------------------------
    # Overall validation
    # ---------------------------------------------------------------

    validation_pass = (
        not missing_tables
        and expected_players_pass
        and expected_supported_pass
        and expected_no_position_pass
        and duplicate_players == 0
        and null_canonical_ids == 0
        and null_claim_ids == 0
        and orphan_claims == 0
        and invalid_position_types == 0
        and invalid_position_count == 0
        and empty_source_positions == 0
        and empty_normalized_positions == 0
        and len(invalid_primary_positions) == 0
        and supported_without_claim_count == 0
        and no_position_with_claims == 0
        and primary_without_main_claim == 0
        and primary_in_secondary == 0
        and invalid_providers == 0
        and non_200_claims == 0
    )

    # ---------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------

    report = {
        "database": DB_PATH,
        "canonical_players": player_count,
        "position_claims": claim_count,
        "duplicate_players": duplicate_players,
        "null_canonical_ids": null_canonical_ids,
        "null_claim_ids": null_claim_ids,
        "orphan_claims": orphan_claims,
        "invalid_position_types": invalid_position_types,
        "invalid_positions": invalid_positions,
        "empty_source_positions": empty_source_positions,
        "empty_normalized_positions": empty_normalized_positions,
        "invalid_primary_positions": invalid_primary_positions,
        "supported_without_claims": supported_without_claim_count,
        "no_position_with_claims": no_position_with_claims,
        "primary_without_main_claim": primary_without_main_claim,
        "primary_in_secondary": primary_in_secondary,
        "invalid_providers": invalid_providers,
        "non_200_claims": non_200_claims,
        "validation_status": (
            "PASS"
            if validation_pass
            else "FAIL"
        )
    }

    Path(
        OUTPUT_JSON
    ).write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    con.close()

    print()
    print("=" * 80)
    print("FINAL AUDIT RESULT")
    print("=" * 80)

    if validation_pass:

        print(
            "STATUS: PASS"
        )

        print(
            "Position evidence test database "
            "passed all validation checks."
        )

    else:

        print(
            "STATUS: FAIL"
        )

        print(
            "One or more validation checks failed."
        )

    print()

    print(
        f"Audit report: {OUTPUT_JSON}"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()