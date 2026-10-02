import duckdb
import json
import csv
from pathlib import Path
from collections import Counter


# ============================================================
# REEP PLAYER FIELD COMPLETENESS AUDIT
# ============================================================
# READ-ONLY — source database will NOT be modified.
#
# Checks completeness of core player fields:
#   - reep_id
#   - label
#   - status
#   - gender
#   - country
#
# Produces:
#   output\reep-player-field-completeness.csv
#   output\reep-player-field-completeness.json
# ============================================================


print("=" * 70)
print("REEP PLAYER FIELD COMPLETENESS AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = (
    BASE_DIR.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

OUTPUT_DIR = BASE_DIR / "output"

CSV_PATH = OUTPUT_DIR / "reep-player-field-completeness.csv"
JSON_PATH = OUTPUT_DIR / "reep-player-field-completeness.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


print("Database:")
print(DB_PATH)
print()


# ------------------------------------------------------------
# CONNECT READ-ONLY
# ------------------------------------------------------------

print("Connecting to REEP database...")

try:
    con = duckdb.connect(str(DB_PATH), read_only=True)
except Exception as e:
    print()
    print("ERROR: Could not connect to the REEP database.")
    print(e)
    raise SystemExit(1)

print("Connected successfully.")
print()


# ------------------------------------------------------------
# VERIFY PLAYERS TABLE
# ------------------------------------------------------------

tables = con.execute(
    """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'main'
    """
).fetchall()

table_names = {row[0] for row in tables}

if "players" not in table_names:
    print("ERROR: 'players' table was not found.")
    con.close()
    raise SystemExit(1)


# ------------------------------------------------------------
# DISCOVER PLAYER SCHEMA
# ------------------------------------------------------------

print("=" * 70)
print("CHECKING PLAYER TABLE SCHEMA")
print("=" * 70)

schema_rows = con.execute(
    "PRAGMA table_info('players')"
).fetchall()

player_columns = [row[1] for row in schema_rows]

print("Players table columns:")
print(", ".join(player_columns))
print()


required_columns = [
    "reep_id",
    "label",
    "status",
    "gender",
    "country",
]

missing_columns = [
    column
    for column in required_columns
    if column not in player_columns
]

if missing_columns:
    print("ERROR: Required columns are missing:")
    for column in missing_columns:
        print(f"  - {column}")

    con.close()
    raise SystemExit(1)


# ------------------------------------------------------------
# LOAD CORE PLAYER DATA
# ------------------------------------------------------------

print("=" * 70)
print("LOADING PLAYER MASTER")
print("=" * 70)

query = """
SELECT
    reep_id,
    label,
    status,
    gender,
    country
FROM players
"""

rows = con.execute(query).fetchall()

print(f"Players loaded: {len(rows):,}")
print()


# ------------------------------------------------------------
# BASIC COUNTS
# ------------------------------------------------------------

total_players = len(rows)

unique_ids = len({
    row[0]
    for row in rows
    if row[0] is not None
})

duplicate_id_count = total_players - unique_ids


# ------------------------------------------------------------
# FIELD ANALYSIS
# ------------------------------------------------------------

field_stats = {}

for index, field in enumerate(required_columns):

    values = [row[index] for row in rows]

    missing = sum(
        1
        for value in values
        if value is None
    )

    blank = sum(
        1
        for value in values
        if isinstance(value, str) and not value.strip()
    )

    present = total_players - missing - blank

    completeness = (
        (present / total_players) * 100
        if total_players
        else 0
    )

    field_stats[field] = {
        "total": total_players,
        "present": present,
        "missing": missing,
        "blank": blank,
        "completeness_percent": round(completeness, 2),
    }


# ------------------------------------------------------------
# CORE RECORD COMPLETENESS
# ------------------------------------------------------------

missing_fields_counter = Counter()

complete_records = 0
incomplete_records = 0

player_results = []


for row in rows:

    reep_id, label, status, gender, country = row

    missing_fields = []

    values = {
        "reep_id": reep_id,
        "label": label,
        "status": status,
        "gender": gender,
        "country": country,
    }

    for field, value in values.items():

        if value is None:
            missing_fields.append(field)

        elif isinstance(value, str) and not value.strip():
            missing_fields.append(field)

    for field in missing_fields:
        missing_fields_counter[field] += 1

    core_complete = len(missing_fields) == 0

    if core_complete:
        complete_records += 1
    else:
        incomplete_records += 1

    player_results.append({
        "reep_id": reep_id,
        "label": label,
        "status": status,
        "gender": gender,
        "country": country,
        "missing_fields": "|".join(missing_fields),
        "core_complete": core_complete,
    })


core_completeness = (
    (complete_records / total_players) * 100
    if total_players
    else 0
)


# ------------------------------------------------------------
# STATUS DISTRIBUTION
# ------------------------------------------------------------

status_counter = Counter()

for row in rows:
    value = row[2]

    if value is None or (
        isinstance(value, str) and not value.strip()
    ):
        status_counter["NULL/BLANK"] += 1
    else:
        status_counter[str(value)] += 1


# ------------------------------------------------------------
# GENDER DISTRIBUTION
# ------------------------------------------------------------

gender_counter = Counter()

for row in rows:
    value = row[3]

    if value is None or (
        isinstance(value, str) and not value.strip()
    ):
        gender_counter["NULL/BLANK"] += 1
    else:
        gender_counter[str(value)] += 1


# ------------------------------------------------------------
# COUNTRY DISTRIBUTION
# ------------------------------------------------------------

country_counter = Counter()

for row in rows:
    value = row[4]

    if value is None or (
        isinstance(value, str) and not value.strip()
    ):
        country_counter["NULL/BLANK"] += 1
    else:
        country_counter[str(value)] += 1


# ------------------------------------------------------------
# PRINT SUMMARY
# ------------------------------------------------------------

print("=" * 70)
print("PLAYER FIELD COMPLETENESS SUMMARY")
print("=" * 70)

print()
print(f"Total players:              {total_players:,}")
print(f"Unique REEP IDs:            {unique_ids:,}")
print(f"Duplicate REEP IDs:         {duplicate_id_count:,}")

print()
print("FIELD COMPLETENESS")
print("-" * 70)

for field in required_columns:

    stats = field_stats[field]

    print(
        f"{field:<12} "
        f"present={stats['present']:,}  "
        f"missing={stats['missing']:,}  "
        f"blank={stats['blank']:,}  "
        f"complete={stats['completeness_percent']:.2f}%"
    )


print()
print("CORE RECORD COMPLETENESS")
print("-" * 70)

print(f"Complete core records:       {complete_records:,}")
print(f"Incomplete core records:     {incomplete_records:,}")
print(f"Core completeness:           {core_completeness:.2f}%")


print()
print("MISSING FIELD COUNTS")
print("-" * 70)

for field in required_columns:

    print(
        f"{field:<12} "
        f"{missing_fields_counter.get(field, 0):,}"
    )


print()
print("STATUS DISTRIBUTION")
print("-" * 70)

for value, count in status_counter.most_common():

    print(
        f"{value:<20} {count:,}"
    )


print()
print("GENDER DISTRIBUTION")
print("-" * 70)

for value, count in gender_counter.most_common():

    print(
        f"{value:<20} {count:,}"
    )


print()
print("COUNTRY DISTRIBUTION")
print("-" * 70)

country_null = country_counter.get("NULL/BLANK", 0)

print(f"Distinct non-empty countries: {len(country_counter) - (1 if country_null else 0):,}")
print(f"NULL/BLANK country:           {country_null:,}")

print()
print("Top 20 country values:")

for value, count in country_counter.most_common(20):

    print(
        f"  {value:<25} {count:,}"
    )


# ------------------------------------------------------------
# WRITE PLAYER-LEVEL CSV
# ------------------------------------------------------------

print()
print("=" * 70)
print("WRITING PLAYER-LEVEL CSV")
print("=" * 70)

with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "reep_id",
            "label",
            "status",
            "gender",
            "country",
            "missing_fields",
            "core_complete",
        ],
    )

    writer.writeheader()
    writer.writerows(player_results)

print(f"CSV written:")
print(CSV_PATH)


# ------------------------------------------------------------
# JSON SUMMARY
# ------------------------------------------------------------

summary = {
    "audit": "REEP Player Field Completeness Audit",
    "read_only": True,
    "database": str(DB_PATH),

    "totals": {
        "players": total_players,
        "unique_reep_ids": unique_ids,
        "duplicate_reep_ids": duplicate_id_count,
    },

    "field_completeness": field_stats,

    "core_record_completeness": {
        "complete_records": complete_records,
        "incomplete_records": incomplete_records,
        "completeness_percent": round(
            core_completeness,
            2
        ),
    },

    "missing_field_counts": dict(
        missing_fields_counter
    ),

    "status_distribution": dict(
        status_counter
    ),

    "gender_distribution": dict(
        gender_counter
    ),

    "country_distribution": dict(
        country_counter
    ),

    "outputs": {
        "csv": str(CSV_PATH),
        "json": str(JSON_PATH),
    },
}


print()
print("=" * 70)
print("WRITING JSON SUMMARY")
print("=" * 70)

with open(
    JSON_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        summary,
        f,
        indent=2,
        ensure_ascii=False,
    )

print(f"JSON written:")
print(JSON_PATH)


# ------------------------------------------------------------
# CLOSE
# ------------------------------------------------------------

con.close()

print()
print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
print()
print("Source database was NOT modified.")
print()