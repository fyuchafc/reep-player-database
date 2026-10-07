"""
REEP PLAYER POSITION SOURCE AUDIT

READ-ONLY AUDIT.
The source REEP database will NOT be modified.

Purpose:
- Discover all source tables/columns related to position/role/formation/lineup.
- Inspect possible player-position evidence.
- Measure player coverage.
- Identify whether position data is player-level or match-level.
- Inspect likely position values.
- Identify external-ID pathways that may support later enrichment.

Source:
data\reep-register-v1.duckdb
"""

from pathlib import Path
import duckdb
import json
import re
from collections import Counter, defaultdict


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DB = (
    Path(r"C:\Users\ADMIN\OneDrive\Documents\important database files")
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

JSON_OUTPUT = OUTPUT_DIR / "reep-player-position-source-audit.json"
CSV_OUTPUT = OUTPUT_DIR / "reep-player-position-source-columns.csv"


# ============================================================
# POSITION-RELATED KEYWORDS
# ============================================================

KEYWORDS = [
    "position",
    "pos",
    "role",
    "formation",
    "lineup",
    "line_up",
    "starting",
    "starter",
    "substitute",
    "bench",
    "squad",
]


# ============================================================
# HELPERS
# ============================================================

def clean(value):
    if value is None:
        return None
    return str(value).strip()


def is_position_like_column(column_name):
    name = column_name.lower()

    for keyword in KEYWORDS:
        if keyword in name:
            return True

    return False


def safe_identifier(value):
    """
    DuckDB identifier quoting.
    """
    return '"' + str(value).replace('"', '""') + '"'


def table_exists(con, table_name):
    row = con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'main'
          AND table_name = ?
        """,
        [table_name],
    ).fetchone()

    return row[0] > 0


# ============================================================
# START
# ============================================================

print("=" * 70)
print("REEP PLAYER POSITION SOURCE AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()
print("Source database:")
print(SOURCE_DB)
print()


if not SOURCE_DB.exists():
    raise FileNotFoundError(
        f"Source database not found:\n{SOURCE_DB}"
    )


print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    str(SOURCE_DB),
    read_only=True,
)

print("Connected successfully.")
print()


# ============================================================
# DATABASE TABLE INVENTORY
# ============================================================

print("=" * 70)
print("DATABASE TABLE INVENTORY")
print("=" * 70)

tables = con.execute(
    """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'main'
    ORDER BY table_name
    """
).fetchall()

table_names = [row[0] for row in tables]

print(f"Tables found: {len(table_names)}")
print()

for table_name in table_names:
    count = con.execute(
        f"SELECT COUNT(*) FROM {safe_identifier(table_name)}"
    ).fetchone()[0]

    print(f"  {table_name:<30} {count:>12,}")

print()


# ============================================================
# COMPLETE COLUMN INVENTORY
# ============================================================

print("=" * 70)
print("SEARCHING FOR POSITION-RELATED COLUMNS")
print("=" * 70)

columns = con.execute(
    """
    SELECT
        table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema = 'main'
    ORDER BY table_name, ordinal_position
    """
).fetchall()


position_columns = []

for table_name, column_name, data_type in columns:
    if is_position_like_column(column_name):
        position_columns.append(
            {
                "table": table_name,
                "column": column_name,
                "data_type": data_type,
            }
        )


print(f"Position-related columns found: {len(position_columns)}")
print()

if position_columns:
    for item in position_columns:
        print(
            f"  {item['table']}.{item['column']} "
            f"({item['data_type']})"
        )
else:
    print("  NONE FOUND")

print()


# ============================================================
# WRITE COLUMN AUDIT CSV
# ============================================================

with open(CSV_OUTPUT, "w", encoding="utf-8") as f:
    f.write("table,column,data_type\n")

    for item in position_columns:
        f.write(
            f"\"{item['table']}\","
            f"\"{item['column']}\","
            f"\"{item['data_type']}\"\n"
        )


# ============================================================
# INSPECT POSITION-RELATED COLUMNS
# ============================================================

column_inspections = []

print("=" * 70)
print("INSPECTING POSITION-RELATED COLUMNS")
print("=" * 70)

for item in position_columns:

    table_name = item["table"]
    column_name = item["column"]

    print()
    print(
        f"TABLE: {table_name} | "
        f"COLUMN: {column_name}"
    )

    quoted_table = safe_identifier(table_name)
    quoted_column = safe_identifier(column_name)

    try:
        total_rows = con.execute(
            f"""
            SELECT COUNT(*)
            FROM {quoted_table}
            WHERE {quoted_column} IS NOT NULL
              AND TRIM(CAST({quoted_column} AS VARCHAR)) <> ''
            """
        ).fetchone()[0]

        distinct_values = con.execute(
            f"""
            SELECT COUNT(DISTINCT CAST({quoted_column} AS VARCHAR))
            FROM {quoted_table}
            WHERE {quoted_column} IS NOT NULL
              AND TRIM(CAST({quoted_column} AS VARCHAR)) <> ''
            """
        ).fetchone()[0]

        print(f"  Non-empty rows:       {total_rows:,}")
        print(f"  Distinct values:      {distinct_values:,}")

        sample_rows = con.execute(
            f"""
            SELECT
                CAST({quoted_column} AS VARCHAR) AS value,
                COUNT(*) AS occurrences
            FROM {quoted_table}
            WHERE {quoted_column} IS NOT NULL
              AND TRIM(CAST({quoted_column} AS VARCHAR)) <> ''
            GROUP BY CAST({quoted_column} AS VARCHAR)
            ORDER BY occurrences DESC, value
            LIMIT 50
            """
        ).fetchall()

        print("  Top values:")

        values = []

        for value, occurrences in sample_rows:
            value = clean(value)

            print(
                f"    {value!r:<40} "
                f"{occurrences:,}"
            )

            values.append(
                {
                    "value": value,
                    "occurrences": occurrences,
                }
            )

        column_inspections.append(
            {
                "table": table_name,
                "column": column_name,
                "data_type": item["data_type"],
                "non_empty_rows": total_rows,
                "distinct_values": distinct_values,
                "top_values": values,
            }
        )

    except Exception as exc:

        print(f"  ERROR: {exc}")

        column_inspections.append(
            {
                "table": table_name,
                "column": column_name,
                "data_type": item["data_type"],
                "error": str(exc),
            }
        )


print()


# ============================================================
# PLAYER TABLE POSITION SEARCH
# ============================================================

print("=" * 70)
print("PLAYER-LEVEL POSITION CHECK")
print("=" * 70)

player_tables = [
    name
    for name in table_names
    if name.lower() in {
        "players",
        "entities",
        "entity_search",
    }
]

player_position_candidates = []

for table_name in player_tables:

    table_columns = [
        row[1]
        for row in columns
        if row[0] == table_name
    ]

    matching = [
        column
        for column in table_columns
        if is_position_like_column(column)
    ]

    if matching:
        player_position_candidates.append(
            {
                "table": table_name,
                "columns": matching,
            }
        )


if player_position_candidates:

    for item in player_position_candidates:
        print(
            f"  {item['table']}: "
            f"{', '.join(item['columns'])}"
        )

else:

    print(
        "  No explicit position column found in "
        "players/entities/entity_search."
    )

print()


# ============================================================
# SEARCH FOR PLAYER ID + POSITION COMBINATIONS
# ============================================================

print("=" * 70)
print("SEARCHING FOR PLAYER-ID + POSITION EVIDENCE")
print("=" * 70)

player_id_names = {
    "reep_id",
    "player_id",
    "entity_id",
    "person_id",
}

player_position_tables = []

for table_name, column_name, data_type in columns:

    if not is_position_like_column(column_name):
        continue

    table_columns = {
        row[1].lower()
        for row in columns
        if row[0] == table_name
    }

    id_matches = player_id_names.intersection(table_columns)

    if id_matches:

        player_position_tables.append(
            {
                "table": table_name,
                "position_column": column_name,
                "player_id_columns": sorted(id_matches),
            }
        )


if player_position_tables:

    for item in player_position_tables:

        print(
            f"  {item['table']}: "
            f"{item['position_column']} "
            f"+ IDs {', '.join(item['player_id_columns'])}"
        )

else:

    print(
        "  No table currently identified as having both "
        "a player/entity ID and a position-like column."
    )

print()


# ============================================================
# MATCH TABLE INSPECTION
# ============================================================

print("=" * 70)
print("MATCH / LINEUP TABLE INSPECTION")
print("=" * 70)

match_like_tables = [
    name
    for name in table_names
    if any(
        keyword in name.lower()
        for keyword in [
            "match",
            "lineup",
            "line_up",
            "event",
            "appearance",
            "squad",
        ]
    )
]

if match_like_tables:

    for table_name in match_like_tables:

        table_columns = [
            row
            for row in columns
            if row[0] == table_name
        ]

        print()
        print(f"  TABLE: {table_name}")

        for _, column_name, data_type in table_columns:
            print(
                f"    {column_name:<30} {data_type}"
            )

else:

    print("  No match/lineup/appearance/squad-named tables found.")

print()


# ============================================================
# SEARCH ALL COLUMNS FOR LIKELY POSITION VALUES
# ============================================================

print("=" * 70)
print("POSITION VALUE DISCOVERY")
print("=" * 70)

position_value_patterns = [
    r"\bgoalkeeper\b",
    r"\bkeeper\b",
    r"\bdefender\b",
    r"\bcentre[- ]back\b",
    r"\bcenter[- ]back\b",
    r"\bfull[- ]back\b",
    r"\bleft[- ]back\b",
    r"\bright[- ]back\b",
    r"\bwing[- ]back\b",
    r"\bmidfielder\b",
    r"\bdefensive midfielder\b",
    r"\bcentral midfielder\b",
    r"\battacking midfielder\b",
    r"\bwinger\b",
    r"\bleft winger\b",
    r"\bright winger\b",
    r"\bforward\b",
    r"\bstriker\b",
    r"\bcentre[- ]forward\b",
    r"\bcenter[- ]forward\b",
    r"\bsecond striker\b",
]

position_regex = re.compile(
    "|".join(position_value_patterns),
    flags=re.IGNORECASE,
)

value_hits = []

for table_name, column_name, data_type in columns:

    quoted_table = safe_identifier(table_name)
    quoted_column = safe_identifier(column_name)

    # Avoid scanning huge binary/complex columns.
    if data_type.upper() not in {
        "VARCHAR",
        "TEXT",
        "STRING",
    }:
        continue

    try:

        rows = con.execute(
            f"""
            SELECT
                CAST({quoted_column} AS VARCHAR)
            FROM {quoted_table}
            WHERE {quoted_column} IS NOT NULL
              AND TRIM(CAST({quoted_column} AS VARCHAR)) <> ''
            LIMIT 100000
            """
        ).fetchall()

        local_hits = Counter()

        for (value,) in rows:

            value = clean(value)

            if value and position_regex.search(value):
                local_hits[value] += 1

        if local_hits:

            print()
            print(
                f"  {table_name}.{column_name}"
            )

            for value, count in local_hits.most_common(30):

                print(
                    f"    {value!r:<45} "
                    f"{count:,}"
                )

                value_hits.append(
                    {
                        "table": table_name,
                        "column": column_name,
                        "value": value,
                        "count_in_sample": count,
                    }
                )

    except Exception:
        pass


if not value_hits:
    print("  No obvious football-position values discovered.")

print()


# ============================================================
# EXTERNAL ID / BRIDGE POSITION CONTEXT
# ============================================================

print("=" * 70)
print("EXTERNAL-ID POSITION ENRICHMENT PATHWAY")
print("=" * 70)

if table_exists(con, "bridges"):

    bridge_columns = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'main'
          AND table_name = 'bridges'
        ORDER BY ordinal_position
        """
    ).fetchall()

    bridge_column_names = [
        row[0]
        for row in bridge_columns
    ]

    print("  bridges columns:")
    for column in bridge_column_names:
        print(f"    {column}")

    print()

    if {
        "provider",
        "namespace",
        "reep_id",
    }.issubset(set(bridge_column_names)):

        provider_rows = con.execute(
            """
            SELECT
                provider,
                namespace,
                COUNT(*) AS rows,
                COUNT(DISTINCT reep_id) AS players
            FROM bridges
            WHERE reep_id IS NOT NULL
            GROUP BY provider, namespace
            ORDER BY players DESC, provider, namespace
            LIMIT 100
            """
        ).fetchall()

        print("  Top external-ID provider mappings:")

        for provider, namespace, rows, players in provider_rows:

            print(
                f"    {provider:<30} "
                f"{namespace:<15} "
                f"rows={rows:,} "
                f"players={players:,}"
            )

else:

    print("  bridges table not found.")

print()


# ============================================================
# SAVE JSON REPORT
# ============================================================

report = {
    "source_database": str(SOURCE_DB),
    "read_only": True,
    "table_count": len(table_names),
    "tables": table_names,
    "position_related_columns": position_columns,
    "column_inspections": column_inspections,
    "player_position_candidates": player_position_candidates,
    "player_position_tables": player_position_tables,
    "match_like_tables": match_like_tables,
    "position_value_hits": value_hits,
}


with open(JSON_OUTPUT, "w", encoding="utf-8") as f:
    json.dump(
        report,
        f,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# FINAL
# ============================================================

print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)

print()
print(f"JSON report:")
print(JSON_OUTPUT)

print()
print(f"CSV report:")
print(CSV_OUTPUT)

print()
print("IMPORTANT:")
print("No REEP source database changes were made.")
print("No v1.0.0 master database changes were made.")
print()

con.close()