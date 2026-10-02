"""
Extract the authoritative REEP player master.

SOURCE:
    REEP register DuckDB
    ../fyucha-player-database-main/.../data/reep-register-v1.duckdb

IMPORTANT:
    - The source DuckDB is opened READ-ONLY.
    - No source tables are modified.
    - No FYUCHA matching is performed.
    - No DOBs, nationality, or other missing data are invented.
    - REEP's reep_id remains the authoritative player identity.

OUTPUT:
    output/players.json
    output/players.csv

PLAYER MASTER FIELDS:
    reep_id
    status
    label
    gender
    country
    corroboration_grade
    corroboration_count
    source_tier_band
"""

from pathlib import Path
import csv
import json
import sys

import duckdb


# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_DB = (
    PROJECT_ROOT.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

OUTPUT_DIR = PROJECT_ROOT / "output"

PLAYERS_JSON = OUTPUT_DIR / "players.json"
PLAYERS_CSV = OUTPUT_DIR / "players.csv"


# ---------------------------------------------------------------------------
# EXPECTED SCHEMA
# ---------------------------------------------------------------------------

EXPECTED_PLAYERS_COLUMNS = {
    "reep_id",
    "status",
    "label",
    "gender",
    "country",
}

EXPECTED_ENTITIES_COLUMNS = {
    "reep_id",
    "entity_type",
    "status",
    "label",
    "gender",
    "country",
    "corroboration_grade",
    "corroboration_count",
    "source_tier_band",
}


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def fail(message):
    print()
    print("ERROR:")
    print(message)
    print()
    sys.exit(1)


def get_columns(con, table_name):
    rows = con.execute(f"DESCRIBE {table_name}").fetchall()
    return {row[0] for row in rows}


def validate_schema(con):
    print("Validating source schema...")

    players_columns = get_columns(con, "main.players")
    entities_columns = get_columns(con, "main.entities")

    missing_players = EXPECTED_PLAYERS_COLUMNS - players_columns
    missing_entities = EXPECTED_ENTITIES_COLUMNS - entities_columns

    if missing_players:
        fail(
            "main.players is missing expected columns: "
            + ", ".join(sorted(missing_players))
        )

    if missing_entities:
        fail(
            "main.entities is missing expected columns: "
            + ", ".join(sorted(missing_entities))
        )

    print("  main.players schema: OK")
    print("  main.entities schema: OK")


def validate_source_relationship(con):
    print()
    print("Validating players ↔ entities relationship...")

    result = con.execute(
        """
        SELECT
            COUNT(*) AS total_players,
            COUNT(e.reep_id) AS matching_entities,
            COUNT(*) - COUNT(e.reep_id) AS missing_entities
        FROM main.players p
        LEFT JOIN main.entities e
            ON p.reep_id = e.reep_id
           AND e.entity_type = 'player'
        """
    ).fetchone()

    total_players, matching_entities, missing_entities = result

    print(f"  Players:             {total_players:,}")
    print(f"  Matching entities:   {matching_entities:,}")
    print(f"  Missing entities:    {missing_entities:,}")

    if missing_entities != 0:
        fail(
            "Not every player has a matching entity record. "
            "Extraction stopped."
        )

    return total_players


def validate_identity_uniqueness(con):
    print()
    print("Validating REEP identity uniqueness...")

    result = con.execute(
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT reep_id) AS unique_reep_ids,
            COUNT(*) - COUNT(DISTINCT reep_id) AS duplicate_rows
        FROM main.players
        """
    ).fetchone()

    total_rows, unique_ids, duplicate_rows = result

    print(f"  Total rows:          {total_rows:,}")
    print(f"  Unique REEP IDs:     {unique_ids:,}")
    print(f"  Duplicate rows:      {duplicate_rows:,}")

    if duplicate_rows != 0:
        fail(
            "Duplicate reep_id values detected in main.players. "
            "Extraction stopped."
        )


def validate_core_agreement(con):
    print()
    print("Validating players ↔ entities core-field agreement...")

    result = con.execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN p.status IS DISTINCT FROM e.status
                    THEN 1 ELSE 0
                END
            ) AS status_diff,
            SUM(
                CASE
                    WHEN p.label IS DISTINCT FROM e.label
                    THEN 1 ELSE 0
                END
            ) AS label_diff,
            SUM(
                CASE
                    WHEN p.gender IS DISTINCT FROM e.gender
                    THEN 1 ELSE 0
                END
            ) AS gender_diff,
            SUM(
                CASE
                    WHEN p.country IS DISTINCT FROM e.country
                    THEN 1 ELSE 0
                END
            ) AS country_diff
        FROM main.players p
        JOIN main.entities e
            ON p.reep_id = e.reep_id
        WHERE e.entity_type = 'player'
        """
    ).fetchone()

    total, status_diff, label_diff, gender_diff, country_diff = result

    print(f"  Records checked:     {total:,}")
    print(f"  Status differences:  {status_diff:,}")
    print(f"  Label differences:   {label_diff:,}")
    print(f"  Gender differences:  {gender_diff:,}")
    print(f"  Country differences: {country_diff:,}")

    if any(
        value != 0
        for value in (
            status_diff,
            label_diff,
            gender_diff,
            country_diff,
        )
    ):
        fail(
            "players and entities disagree on one or more core fields. "
            "Extraction stopped."
        )


def extract_players(con):
    print()
    print("Extracting REEP player master...")

    rows = con.execute(
        """
        SELECT
            p.reep_id,
            p.status,
            p.label,
            p.gender,
            p.country,
            e.corroboration_grade,
            e.corroboration_count,
            e.source_tier_band
        FROM main.players p
        JOIN main.entities e
            ON p.reep_id = e.reep_id
        WHERE e.entity_type = 'player'
        ORDER BY p.reep_id
        """
    ).fetchall()

    columns = [
        "reep_id",
        "status",
        "label",
        "gender",
        "country",
        "corroboration_grade",
        "corroboration_count",
        "source_tier_band",
    ]

    players = [
        dict(zip(columns, row))
        for row in rows
    ]

    print(f"  Players extracted:  {len(players):,}")

    if not players:
        fail("No players were extracted.")

    return players, columns


def validate_extracted_players(players):
    print()
    print("Validating extracted player master...")

    ids = [player["reep_id"] for player in players]

    if len(ids) != len(set(ids)):
        fail("Duplicate reep_id values found in extracted output.")

    required_fields = {
        "reep_id",
        "status",
        "label",
        "gender",
        "country",
        "corroboration_grade",
        "corroboration_count",
        "source_tier_band",
    }

    for index, player in enumerate(players, start=1):
        missing = required_fields - set(player.keys())

        if missing:
            fail(
                f"Player record {index} is missing fields: "
                + ", ".join(sorted(missing))
            )

        if not player["reep_id"]:
            fail(f"Player record {index} has an empty reep_id.")

        if not player["label"]:
            fail(
                f"Player {player['reep_id']} has an empty canonical label."
            )

    print(f"  Unique REEP IDs:     {len(set(ids)):,}")
    print("  Required fields:     OK")
    print("  Empty REEP IDs:      0")
    print("  Empty labels:        0")


def write_json(players):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with PLAYERS_JSON.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        json.dump(
            players,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    print(f"  JSON written:        {PLAYERS_JSON}")


def write_csv(players, columns):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with PLAYERS_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=columns,
        )

        writer.writeheader()
        writer.writerows(players)

    print(f"  CSV written:         {PLAYERS_CSV}")


def print_summary(con, players):
    print()
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)

    print(f"REEP players:          {len(players):,}")
    print(f"JSON records:           {len(players):,}")
    print(f"CSV records:            {len(players):,}")

    print()
    print("Status distribution:")

    rows = con.execute(
        """
        SELECT
            COALESCE(status, 'NULL') AS status,
            COUNT(*) AS players
        FROM main.players
        GROUP BY status
        ORDER BY players DESC
        """
    ).fetchall()

    for status, count in rows:
        print(f"  {status:<15} {count:>10,}")

    print()
    print("Gender distribution:")

    rows = con.execute(
        """
        SELECT
            COALESCE(gender, 'NULL') AS gender,
            COUNT(*) AS players
        FROM main.players
        GROUP BY gender
        ORDER BY players DESC
        """
    ).fetchall()

    for gender, count in rows:
        print(f"  {gender:<15} {count:>10,}")

    print()
    print("Output files:")
    print(f"  {PLAYERS_JSON}")
    print(f"  {PLAYERS_CSV}")
    print()
    print("Source database was opened READ-ONLY.")
    print("No FYUCHA matching was performed.")
    print("No source database tables were modified.")
    print("=" * 70)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("REEP PLAYER EXTRACTION")
    print("=" * 70)

    print()
    print(f"Project root:")
    print(f"  {PROJECT_ROOT}")

    print()
    print(f"Source database:")
    print(f"  {SOURCE_DB}")

    if not SOURCE_DB.exists():
        fail(
            "REEP source database was not found at:\n"
            + str(SOURCE_DB)
        )

    print()
    print("Opening REEP database READ-ONLY...")

    con = None

    try:
        con = duckdb.connect(
            str(SOURCE_DB),
            read_only=True,
        )

        print("  Connection: OK")

        validate_schema(con)

        total_players = validate_source_relationship(con)

        validate_identity_uniqueness(con)

        validate_core_agreement(con)

        players, columns = extract_players(con)

        if len(players) != total_players:
            fail(
                "Extracted player count does not match source player count."
            )

        validate_extracted_players(players)

        print()
        print("Writing extracted files...")

        write_json(players)
        write_csv(players, columns)

        print_summary(con, players)

    except duckdb.Error as error:
        fail(f"DuckDB error:\n{error}")

    finally:
        if con is not None:
            con.close()


if __name__ == "__main__":
    main()