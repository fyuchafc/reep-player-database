import csv
import json
import duckdb
from pathlib import Path
from datetime import datetime, timezone

INPUT_CSV = "output/reep-transfermarkt-position-v4-25-audit.csv"

OUTPUT_DB = "output/reep-player-position-evidence-test.duckdb"
OUTPUT_REPORT = "output/reep-player-position-evidence-test-build-report.json"


def normalize_position(position):
    """
    Normalize Transfermarkt position names into
    the stable Fyucha position vocabulary.

    Original source wording is preserved separately.
    """

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

    return mapping.get(
        position,
        position
    )


def split_positions(value):
    if not value:
        return []

    return [
        item.strip()
        for item in value.split("|")
        if item.strip()
    ]


def main():

    print("=" * 80)
    print("BUILD REEP POSITION EVIDENCE TEST DATABASE")
    print("=" * 80)
    print()

    print("READ-ONLY SOURCE INPUT:")
    print(INPUT_CSV)
    print()

    print("OUTPUT:")
    print(OUTPUT_DB)
    print()

    # ------------------------------------------------------------------
    # Read validated CSV
    # ------------------------------------------------------------------

    rows = []

    with open(
        INPUT_CSV,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:
            rows.append(row)

    print(
        f"Input rows: {len(rows)}"
    )

    print()

    # ------------------------------------------------------------------
    # Create database
    # ------------------------------------------------------------------

    output_path = Path(OUTPUT_DB)

    if output_path.exists():
        output_path.unlink()

    con = duckdb.connect(
        str(output_path)
    )

    # ------------------------------------------------------------------
    # Raw claims table
    # ------------------------------------------------------------------

    con.execute("""
        CREATE TABLE player_position_claims (
            reep_id VARCHAR NOT NULL,
            label VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
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

    # ------------------------------------------------------------------
    # Canonical player position table
    # ------------------------------------------------------------------

    con.execute("""
        CREATE TABLE player_position (
            reep_id VARCHAR PRIMARY KEY,
            label VARCHAR NOT NULL,
            primary_position VARCHAR,
            secondary_positions VARCHAR,
            position_status VARCHAR NOT NULL,
            evidence_count INTEGER NOT NULL,
            provider_count INTEGER NOT NULL,
            source VARCHAR NOT NULL
        )
    """)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    con.execute("""
        CREATE TABLE database_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR
        )
    """)

    retrieved_at = datetime.now(
        timezone.utc
    ).isoformat()

    # ------------------------------------------------------------------
    # Insert claims
    # ------------------------------------------------------------------

    claim_rows = []

    for row in rows:

        if row["http_status"] != "200":
            continue

        reep_id = row["reep_id"].strip()
        label = row["label"].strip()
        provider_id = row["transfermarkt_id"].strip()
        source_url = row["url"].strip()

        main_positions = split_positions(
            row["main_positions"]
        )

        other_positions = split_positions(
            row["other_positions"]
        )

        for position in main_positions:

            claim_rows.append([
                reep_id,
                label,
                "transfermarkt",
                provider_id,
                position,
                normalize_position(position),
                "main",
                source_url,
                200,
                "transfermarkt-position-parser-v4",
                retrieved_at
            ])

        for position in other_positions:

            claim_rows.append([
                reep_id,
                label,
                "transfermarkt",
                provider_id,
                position,
                normalize_position(position),
                "other",
                source_url,
                200,
                "transfermarkt-position-parser-v4",
                retrieved_at
            ])

    if claim_rows:

        con.executemany("""
            INSERT INTO player_position_claims
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, claim_rows)

    # ------------------------------------------------------------------
    # Build canonical position rows
    # ------------------------------------------------------------------

    canonical_rows = []

    for row in rows:

        if row["http_status"] != "200":
            continue

        reep_id = row["reep_id"].strip()
        label = row["label"].strip()

        main_positions = split_positions(
            row["main_positions"]
        )

        other_positions = split_positions(
            row["other_positions"]
        )

        normalized_main = [
            normalize_position(x)
            for x in main_positions
        ]

        normalized_other = [
            normalize_position(x)
            for x in other_positions
        ]

        if normalized_main:

            primary_position = normalized_main[0]

        else:

            primary_position = None

        secondary = []

        for position in normalized_other:

            if position != primary_position:
                secondary.append(position)

        secondary_positions = (
            " | ".join(
                dict.fromkeys(secondary)
            )
            if secondary
            else None
        )

        if primary_position:

            position_status = "supported"

        else:

            position_status = "no_position"

        evidence_count = (
            len(normalized_main)
            + len(normalized_other)
        )

        provider_count = 1

        canonical_rows.append([
            reep_id,
            label,
            primary_position,
            secondary_positions,
            position_status,
            evidence_count,
            provider_count,
            "transfermarkt"
        ])

    if canonical_rows:

        con.executemany("""
            INSERT INTO player_position
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, canonical_rows)

    # ------------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------------

    con.execute("""
        CREATE INDEX idx_position_claims_reep_id
        ON player_position_claims(reep_id)
    """)

    con.execute("""
        CREATE INDEX idx_position_claims_provider_id
        ON player_position_claims(provider, provider_id)
    """)

    con.execute("""
        CREATE INDEX idx_position_claims_position
        ON player_position_claims(position_normalized)
    """)

    con.execute("""
        CREATE INDEX idx_player_position_primary
        ON player_position(primary_position)
    """)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    metadata = [
        (
            "database_type",
            "REEP v1.1 derived position evidence test"
        ),
        (
            "source",
            "Transfermarkt"
        ),
        (
            "parser_version",
            "transfermarkt-position-parser-v4"
        ),
        (
            "input_file",
            INPUT_CSV
        ),
        (
            "created_at",
            retrieved_at
        ),
        (
            "read_only_source",
            "true"
        ),
        (
            "scope",
            "25-player validation sample"
        )
    ]

    con.executemany("""
        INSERT INTO database_metadata
        VALUES (?, ?)
    """, metadata)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    player_count = con.execute("""
        SELECT COUNT(*)
        FROM player_position
    """).fetchone()[0]

    claim_count = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims
    """).fetchone()[0]

    duplicate_players = con.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT reep_id
            FROM player_position
            GROUP BY reep_id
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    orphan_claims = con.execute("""
        SELECT COUNT(*)
        FROM player_position_claims c
        LEFT JOIN player_position p
            ON c.reep_id = p.reep_id
        WHERE p.reep_id IS NULL
    """).fetchone()[0]

    supported_players = con.execute("""
        SELECT COUNT(*)
        FROM player_position
        WHERE position_status = 'supported'
    """).fetchone()[0]

    no_position_players = con.execute("""
        SELECT COUNT(*)
        FROM player_position
        WHERE position_status = 'no_position'
    """).fetchone()[0]

    distinct_primary = con.execute("""
        SELECT COUNT(DISTINCT primary_position)
        FROM player_position
        WHERE primary_position IS NOT NULL
    """).fetchone()[0]

    validation_pass = (
        player_count == 25
        and duplicate_players == 0
        and orphan_claims == 0
        and claim_count > 0
        and supported_players == 21
        and no_position_players == 4
    )

    # ------------------------------------------------------------------
    # Position distribution
    # ------------------------------------------------------------------

    primary_distribution = con.execute("""
        SELECT
            primary_position,
            COUNT(*) AS players
        FROM player_position
        WHERE primary_position IS NOT NULL
        GROUP BY primary_position
        ORDER BY players DESC, primary_position
    """).fetchall()

    # ------------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------------

    report = {
        "database": OUTPUT_DB,
        "input": INPUT_CSV,
        "players": player_count,
        "position_claims": claim_count,
        "supported_players": supported_players,
        "no_position_players": no_position_players,
        "distinct_primary_positions": distinct_primary,
        "duplicate_players": duplicate_players,
        "orphan_claims": orphan_claims,
        "primary_position_distribution": [
            {
                "position": row[0],
                "players": row[1]
            }
            for row in primary_distribution
        ],
        "validation_status": (
            "PASS"
            if validation_pass
            else "FAIL"
        )
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

    con.close()

    # ------------------------------------------------------------------
    # Final output
    # ------------------------------------------------------------------

    print("=" * 80)
    print("POSITION EVIDENCE DATABASE VALIDATION")
    print("=" * 80)

    print(
        f"Players: {player_count}"
    )

    print(
        f"Position claim rows: {claim_count}"
    )

    print(
        f"Supported players: {supported_players}"
    )

    print(
        f"No-position players: {no_position_players}"
    )

    print(
        f"Distinct primary positions: "
        f"{distinct_primary}"
    )

    print(
        f"Duplicate player IDs: "
        f"{duplicate_players}"
    )

    print(
        f"Orphan claim rows: "
        f"{orphan_claims}"
    )

    print()

    print("PRIMARY POSITION DISTRIBUTION")
    print("-" * 80)

    for position, count in primary_distribution:

        print(
            f"{position}: {count}"
        )

    print()

    print(
        "STATUS: "
        + (
            "PASS"
            if validation_pass
            else "FAIL"
        )
    )

    print()

    print(
        f"Database saved: {OUTPUT_DB}"
    )

    print(
        f"Report saved: {OUTPUT_REPORT}"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()