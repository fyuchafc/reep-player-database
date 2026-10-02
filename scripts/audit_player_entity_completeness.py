import duckdb
import json
import csv
from pathlib import Path
from collections import Counter

# ============================================================
# REEP PLAYER → ENTITY COMPLETENESS AUDIT
#
# READ-ONLY
#
# Purpose:
# Verify that main.players is a complete and exact projection
# of main.entities for entity_type = 'player'.
#
# Source database is NEVER modified.
# Old FYUCHA database is NEVER modified.
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = (
    BASE_DIR.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

# Fallback to the known source path if necessary
if not DB_PATH.exists():
    DB_PATH = Path(
        r"C:\Users\ADMIN\OneDrive\Documents\important database files"
        r"\fyucha-player-database-main\fyucha-player-database-main"
        r"\data\reep-register-v1.duckdb"
    )

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUTPUT = (
    OUTPUT_DIR
    / "reep-player-entity-completeness-audit.json"
)

CSV_OUTPUT = (
    OUTPUT_DIR
    / "reep-player-entity-completeness.csv"
)


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# START
# ============================================================

section("REEP PLAYER → ENTITY COMPLETENESS AUDIT")

if not DB_PATH.exists():
    print()
    print("ERROR: Source database not found:")
    print(DB_PATH)
    raise SystemExit(1)

file_size = DB_PATH.stat().st_size

print()
print(
    f"File size: {file_size:,} bytes "
    f"({file_size / (1024 * 1024):.2f} MiB)"
)

print()
print("OPENING DATABASE READ-ONLY...")

con = duckdb.connect(
    database=str(DB_PATH),
    read_only=True
)


# ============================================================
# VERIFY TABLES
# ============================================================

section("VERIFYING REQUIRED TABLES")

required_tables = {
    "players",
    "entities",
}

existing_tables = {
    row[0]
    for row in con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        """
    ).fetchall()
}

missing_tables = sorted(
    required_tables - existing_tables
)

if missing_tables:
    print("Missing required tables:")

    for table in missing_tables:
        print(f"  - {table}")

    con.close()
    raise SystemExit(1)

print("All required tables found.")


# ============================================================
# READ PLAYERS
# ============================================================

section("READING MASTER PLAYER TABLE")

player_rows = con.execute(
    """
    SELECT
        reep_id,
        status,
        label,
        gender,
        country
    FROM main.players
    """
).fetchall()

players = {}

for reep_id, status, label, gender, country in player_rows:

    players[reep_id] = {
        "reep_id": reep_id,
        "status": status,
        "label": label,
        "gender": gender,
        "country": country,
    }

print(
    f"Players:                  {len(players):,}"
)

print(
    f"Unique player IDs:        "
    f"{len(players):,}"
)


# ============================================================
# READ PLAYER ENTITIES
# ============================================================

section("READING PLAYER ENTITY RECORDS")

entity_rows = con.execute(
    """
    SELECT
        reep_id,
        status,
        label,
        gender,
        country,
        corroboration_grade,
        corroboration_count,
        source_tier_band
    FROM main.entities
    WHERE entity_type = 'player'
    """
).fetchall()

entities = {}

duplicate_entity_ids = []

for (
    reep_id,
    status,
    label,
    gender,
    country,
    corroboration_grade,
    corroboration_count,
    source_tier_band,
) in entity_rows:

    if reep_id in entities:
        duplicate_entity_ids.append(reep_id)

    entities[reep_id] = {
        "reep_id": reep_id,
        "status": status,
        "label": label,
        "gender": gender,
        "country": country,
        "corroboration_grade": corroboration_grade,
        "corroboration_count": corroboration_count,
        "source_tier_band": source_tier_band,
    }

print(
    f"Entity player records:   {len(entity_rows):,}"
)

print(
    f"Unique entity player IDs: "
    f"{len(entities):,}"
)


# ============================================================
# PLAYER → ENTITY COVERAGE
# ============================================================

section("CHECKING PLAYER → ENTITY COVERAGE")

players_missing_from_entities = sorted(
    reep_id
    for reep_id in players
    if reep_id not in entities
)

entities_missing_from_players = sorted(
    reep_id
    for reep_id in entities
    if reep_id not in players
)

print(
    f"Players missing from entities: "
    f"{len(players_missing_from_entities):,}"
)

print(
    f"Entity-only players:            "
    f"{len(entities_missing_from_players):,}"
)

print(
    f"Duplicate player IDs in entities: "
    f"{len(duplicate_entity_ids):,}"
)


# ============================================================
# CORE FIELD COMPARISON
# ============================================================

section("CHECKING CORE FIELD AGREEMENT")

field_differences = Counter()

field_difference_rows = []

common_ids = sorted(
    set(players) & set(entities)
)

for reep_id in common_ids:

    player = players[reep_id]
    entity = entities[reep_id]

    for field in [
        "status",
        "label",
        "gender",
        "country",
    ]:

        if player[field] != entity[field]:

            field_differences[field] += 1

            field_difference_rows.append(
                {
                    "reep_id": reep_id,
                    "field": field,
                    "players_value": player[field],
                    "entities_value": entity[field],
                }
            )

for field in [
    "status",
    "label",
    "gender",
    "country",
]:

    print(
        f"{field:<12} "
        f"{field_differences[field]:,} differences"
    )


# ============================================================
# STATUS DISTRIBUTION
# ============================================================

section("PLAYER STATUS DISTRIBUTION")

player_status = Counter(
    record["status"]
    for record in players.values()
)

for status, count in sorted(
    player_status.items()
):

    print(
        f"{str(status):<20} {count:,}"
    )


# ============================================================
# GENDER DISTRIBUTION
# ============================================================

section("PLAYER GENDER DISTRIBUTION")

player_gender = Counter(
    record["gender"]
    for record in players.values()
)

for gender, count in sorted(
    player_gender.items(),
    key=lambda x: str(x[0])
):

    label = (
        "NULL"
        if gender is None
        else str(gender)
    )

    print(
        f"{label:<20} {count:,}"
    )


# ============================================================
# COUNTRY DISTRIBUTION
# ============================================================

section("PLAYER COUNTRY DISTRIBUTION")

country_counts = Counter(
    record["country"]
    for record in players.values()
)

for country, count in sorted(
    country_counts.items(),
    key=lambda x: str(x[0])
):

    label = (
        "NULL"
        if country is None
        else str(country)
    )

    print(
        f"{label:<20} {count:,}"
    )


# ============================================================
# ENTITY QUALITY
# ============================================================

section("ENTITY QUALITY DISTRIBUTION")

quality_grade = Counter(
    record["corroboration_grade"]
    for record in entities.values()
)

quality_count = Counter(
    record["corroboration_count"]
    for record in entities.values()
)

source_tier = Counter(
    record["source_tier_band"]
    for record in entities.values()
)

print()
print("Corroboration grade:")

for grade, count in sorted(
    quality_grade.items(),
    key=lambda x: str(x[0])
):

    label = (
        "NULL"
        if grade is None
        else str(grade)
    )

    print(
        f"  {label:<18} {count:,}"
    )

print()
print("Corroboration count:")

for count_value, count in sorted(
    quality_count.items(),
    key=lambda x: (
        x[0] is None,
        x[0] if x[0] is not None else -1
    )
):

    label = (
        "NULL"
        if count_value is None
        else str(count_value)
    )

    print(
        f"  {label:<18} {count:,}"
    )

print()
print("Source tier band:")

for band, count in sorted(
    source_tier.items(),
    key=lambda x: str(x[0])
):

    label = (
        "NULL"
        if band is None
        else str(band)
    )

    print(
        f"  {label:<18} {count:,}"
    )


# ============================================================
# LABEL PRESENCE
# ============================================================

section("CHECKING LABEL COMPLETENESS")

players_with_label = sum(
    1
    for record in players.values()
    if record["label"] is not None
    and str(record["label"]).strip() != ""
)

players_without_label = (
    len(players) - players_with_label
)

print(
    f"Players with labels:    "
    f"{players_with_label:,}"
)

print(
    f"Players without labels: "
    f"{players_without_label:,}"
)


# ============================================================
# EXACT RECORD AGREEMENT
# ============================================================

section("CHECKING EXACT CORE RECORD AGREEMENT")

exact_core_matches = 0
exact_core_mismatches = 0

for reep_id in common_ids:

    player = players[reep_id]
    entity = entities[reep_id]

    same = (
        player["reep_id"] == entity["reep_id"]
        and player["status"] == entity["status"]
        and player["label"] == entity["label"]
        and player["gender"] == entity["gender"]
        and player["country"] == entity["country"]
    )

    if same:
        exact_core_matches += 1
    else:
        exact_core_mismatches += 1

print(
    f"Exact core record matches:    "
    f"{exact_core_matches:,}"
)

print(
    f"Exact core record mismatches: "
    f"{exact_core_mismatches:,}"
)


# ============================================================
# QUALITY ATTACHED TO PLAYER RECORDS
# ============================================================

section("CHECKING QUALITY FIELD COVERAGE")

quality_rows = []

for reep_id in common_ids:

    entity = entities[reep_id]

    quality_rows.append(
        {
            "reep_id": reep_id,
            "corroboration_grade":
                entity["corroboration_grade"],
            "corroboration_count":
                entity["corroboration_count"],
            "source_tier_band":
                entity["source_tier_band"],
        }
    )

quality_players = len(quality_rows)

print(
    f"Players with entity quality records: "
    f"{quality_players:,}"
)


# ============================================================
# BUILD AUDIT
# ============================================================

audit = {
    "database": {
        "path": str(DB_PATH),
        "size_bytes": file_size,
        "size_mib": round(
            file_size / (1024 * 1024),
            2
        ),
        "read_only": True,
    },

    "population": {
        "players": len(players),
        "unique_player_ids": len(players),

        "entity_player_records":
            len(entity_rows),

        "unique_entity_player_ids":
            len(entities),

        "players_missing_from_entities":
            len(players_missing_from_entities),

        "entity_only_players":
            len(entities_missing_from_players),

        "duplicate_entity_player_ids":
            len(duplicate_entity_ids),
    },

    "core_field_differences":
        dict(field_differences),

    "exact_core_record_matches":
        exact_core_matches,

    "exact_core_record_mismatches":
        exact_core_mismatches,

    "status_distribution":
        dict(player_status),

    "gender_distribution": {
        (
            "NULL"
            if key is None
            else str(key)
        ): value
        for key, value in player_gender.items()
    },

    "country_distribution": {
        (
            "NULL"
            if key is None
            else str(key)
        ): value
        for key, value in country_counts.items()
    },

    "quality": {
        "corroboration_grade": {
            (
                "NULL"
                if key is None
                else str(key)
            ): value
            for key, value in quality_grade.items()
        },

        "corroboration_count": {
            (
                "NULL"
                if key is None
                else str(key)
            ): value
            for key, value in quality_count.items()
        },

        "source_tier_band": {
            (
                "NULL"
                if key is None
                else str(key)
            ): value
            for key, value in source_tier.items()
        },
    },

    "labels": {
        "with_labels":
            players_with_label,

        "without_labels":
            players_without_label,
    },

    "quality_players":
        quality_players,

    "field_difference_rows":
        field_difference_rows,
}


# ============================================================
# WRITE JSON
# ============================================================

section("WRITING JSON AUDIT")

with JSON_OUTPUT.open(
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        audit,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# WRITE CSV
# ============================================================

section("WRITING CSV AUDIT")

csv_fields = [
    "reep_id",
    "field",
    "players_value",
    "entities_value",
]

with CSV_OUTPUT.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=csv_fields
    )

    writer.writeheader()

    for row in field_difference_rows:
        writer.writerow(row)


# ============================================================
# FINAL
# ============================================================

section("AUDIT COMPLETE")

print()
print("JSON output:")
print(JSON_OUTPUT)

print()
print("CSV output:")
print(CSV_OUTPUT)

print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")

con.close()