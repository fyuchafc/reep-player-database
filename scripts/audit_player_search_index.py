import duckdb
from pathlib import Path
import sys


# ============================================================
# REEP PLAYER SEARCH / INDEX QUALITY AUDIT
# ============================================================
#
# READ-ONLY
# This script does NOT modify the REEP source database.
#
# Uses the actual REEP schema:
#   reep_id
#   entity_type
#   label
#   search_text
#
# Checks:
#   1. Required tables
#   2. Table structures
#   3. Player counts
#   4. Player -> search coverage
#   5. Search rows per player
#   6. Missing player search records
#   7. Duplicate search entries
#   8. Empty / weak search values
#   9. Non-player search contamination
#  10. Orphan search records
#  11. entities vs players consistency
#  12. Search/index consistency
#  13. Sample problem records
#
# ============================================================


DB_PATH = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)


# ============================================================
# HELPERS
# ============================================================

def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def safe_count(con, sql):
    try:
        return con.execute(sql).fetchone()[0]
    except Exception:
        return None


# ============================================================
# START
# ============================================================

print("=" * 70)
print("REEP PLAYER SEARCH / INDEX QUALITY AUDIT")
print("=" * 70)

print()
print("READ-ONLY — source database will NOT be modified.")
print()
print("Source database:")
print(DB_PATH)


if not DB_PATH.exists():
    print()
    print("ERROR: REEP database was not found.")
    print("Check DB_PATH at the top of this script.")
    sys.exit(1)


print()
print("Opening REEP database READ-ONLY...")

try:
    con = duckdb.connect(
        str(DB_PATH),
        read_only=True
    )
except Exception as e:
    print()
    print("ERROR: Could not open database.")
    print(e)
    sys.exit(1)

print("Connected successfully.")


# ============================================================
# REQUIRED TABLES
# ============================================================

section("CHECKING REQUIRED TABLES")

required_tables = [
    "entities",
    "entity_search",
    "aliases",
    "overlay_aliases",
    "bridges",
    "players",
]

existing_tables = []

for table in required_tables:

    try:
        con.execute(
            f"SELECT 1 FROM {table} LIMIT 1"
        )

        print(f"  {table:<20} FOUND")
        existing_tables.append(table)

    except Exception:

        print(f"  {table:<20} NOT FOUND")


for required in ["entities", "entity_search", "players"]:

    if required not in existing_tables:

        print()
        print(f"ERROR: Required table '{required}' is missing.")
        con.close()
        sys.exit(1)


# ============================================================
# DATABASE COUNTS
# ============================================================

section("DATABASE COUNTS")

for table in existing_tables:

    count = safe_count(
        con,
        f"SELECT COUNT(*) FROM {table}"
    )

    if count is not None:

        print(
            f"  {table:<20} {count:,}"
        )


# ============================================================
# TABLE STRUCTURES
# ============================================================

section("SEARCH / PLAYER TABLE STRUCTURE")


for table in [
    "entities",
    "entity_search",
    "players"
]:

    print()
    print(f"{table}:")

    rows = con.execute(
        f"PRAGMA table_info('{table}')"
    ).fetchall()

    for row in rows:

        column_name = row[1]
        column_type = row[2]

        print(
            f"  - {column_name:<25} {column_type}"
        )


# ============================================================
# ENTITY TYPE DISTRIBUTION
# ============================================================

section("ENTITY TYPE DISTRIBUTION")

rows = con.execute(
    """
    SELECT
        entity_type,
        COUNT(*) AS n
    FROM entities
    GROUP BY entity_type
    ORDER BY n DESC
    """
).fetchall()


for entity_type, count in rows:

    print(
        f"  {str(entity_type):<30} {count:,}"
    )


# ============================================================
# PLAYER COUNTS
# ============================================================

section("PLAYER ENTITY COUNTS")


entity_players = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entities
    WHERE entity_type = 'player'
    """
)


players_table = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM players
    """
)


print(
    f"  Player entities : {entity_players:,}"
)

print(
    f"  players table   : {players_table:,}"
)


# ============================================================
# ENTITY / PLAYER ID CONSISTENCY
# ============================================================

section("ENTITIES vs PLAYERS ID CONSISTENCY")


players_missing_from_entities = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM players p
    LEFT JOIN entities e
        ON p.reep_id = e.reep_id
    WHERE e.reep_id IS NULL
    """
)


entities_missing_from_players = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entities e
    LEFT JOIN players p
        ON e.reep_id = p.reep_id
    WHERE e.entity_type = 'player'
      AND p.reep_id IS NULL
    """
)


print(
    f"  players IDs missing from entities : "
    f"{players_missing_from_entities:,}"
)

print(
    f"  player entities missing from players : "
    f"{entities_missing_from_players:,}"
)


# ============================================================
# SEARCH INDEX TOTALS
# ============================================================

section("SEARCH INDEX TOTALS")


search_total = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search
    """
)


print(
    f"  Total entity_search rows : "
    f"{search_total:,}"
)


# ============================================================
# SEARCH ENTITY TYPE DISTRIBUTION
# ============================================================

section("SEARCH INDEX ENTITY TYPE DISTRIBUTION")


rows = con.execute(
    """
    SELECT
        entity_type,
        COUNT(*) AS n
    FROM entity_search
    GROUP BY entity_type
    ORDER BY n DESC
    """
).fetchall()


for entity_type, count in rows:

    print(
        f"  {str(entity_type):<30} {count:,}"
    )


# ============================================================
# PLAYER SEARCH COVERAGE
# ============================================================

section("PLAYER SEARCH COVERAGE")


players_with_search = safe_count(
    con,
    """
    SELECT COUNT(DISTINCT p.reep_id)
    FROM players p
    INNER JOIN entity_search s
        ON p.reep_id = s.reep_id
    """
)


players_without_search = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM players p
    LEFT JOIN entity_search s
        ON p.reep_id = s.reep_id
    WHERE s.reep_id IS NULL
    """
)


print(
    f"  Total players             : {players_table:,}"
)

print(
    f"  Players with search       : "
    f"{players_with_search:,}"
)

print(
    f"  Players without search    : "
    f"{players_without_search:,}"
)


if players_table:

    coverage = (
        players_with_search
        / players_table
    ) * 100

    print(
        f"  Search coverage           : "
        f"{coverage:.4f}%"
    )


# ============================================================
# SEARCH ROWS PER PLAYER
# ============================================================

section("SEARCH ROWS PER PLAYER")


rows = con.execute(
    """
    WITH player_search AS (

        SELECT
            p.reep_id,

            COUNT(s.reep_id) AS search_rows

        FROM players p

        LEFT JOIN entity_search s
            ON p.reep_id = s.reep_id

        GROUP BY
            p.reep_id
    )

    SELECT

        COUNT(*) AS players,

        SUM(
            CASE
                WHEN search_rows = 0
                THEN 1
                ELSE 0
            END
        ) AS zero_rows,

        SUM(
            CASE
                WHEN search_rows = 1
                THEN 1
                ELSE 0
            END
        ) AS one_row,

        SUM(
            CASE
                WHEN search_rows BETWEEN 2 AND 5
                THEN 1
                ELSE 0
            END
        ) AS two_to_five,

        SUM(
            CASE
                WHEN search_rows > 5
                THEN 1
                ELSE 0
            END
        ) AS over_five,

        AVG(search_rows),

        MAX(search_rows)

    FROM player_search
    """
).fetchone()


labels = [
    "Players",
    "Zero search rows",
    "One search row",
    "2–5 search rows",
    "More than 5 search rows",
    "Average search rows",
    "Maximum search rows",
]


for label, value in zip(labels, rows):

    if isinstance(value, float):

        print(
            f"  {label:<30} "
            f"{value:.2f}"
        )

    else:

        print(
            f"  {label:<30} "
            f"{value:,}"
        )


# ============================================================
# SEARCH ROW DUPLICATES
# ============================================================

section("DUPLICATE SEARCH ENTRIES")


duplicate_groups = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM (

        SELECT

            reep_id,

            LOWER(
                TRIM(
                    CAST(search_text AS VARCHAR)
                )
            ) AS search_value,

            COUNT(*) AS n

        FROM entity_search

        WHERE search_text IS NOT NULL

        GROUP BY
            reep_id,
            LOWER(
                TRIM(
                    CAST(search_text AS VARCHAR)
                )
            )

        HAVING COUNT(*) > 1

    )
    """
)


duplicate_extra_rows = safe_count(
    con,
    """
    SELECT COALESCE(
        SUM(n - 1),
        0
    )

    FROM (

        SELECT

            reep_id,

            LOWER(
                TRIM(
                    CAST(search_text AS VARCHAR)
                )
            ) AS search_value,

            COUNT(*) AS n

        FROM entity_search

        WHERE search_text IS NOT NULL

        GROUP BY
            reep_id,
            LOWER(
                TRIM(
                    CAST(search_text AS VARCHAR)
                )
            )

        HAVING COUNT(*) > 1

    )
    """
)


print(
    f"  Duplicate search groups : "
    f"{duplicate_groups:,}"
)

print(
    f"  Extra duplicate rows    : "
    f"{duplicate_extra_rows:,}"
)


# ============================================================
# EMPTY / WEAK SEARCH VALUES
# ============================================================

section("EMPTY / WEAK SEARCH VALUES")


empty_values = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search
    WHERE search_text IS NULL
       OR TRIM(
            CAST(search_text AS VARCHAR)
          ) = ''
    """
)


short_values = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search
    WHERE search_text IS NOT NULL
      AND LENGTH(
            TRIM(
                CAST(search_text AS VARCHAR)
            )
          ) BETWEEN 1 AND 2
    """
)


print(
    f"  NULL / empty search values : "
    f"{empty_values:,}"
)

print(
    f"  1–2 character values       : "
    f"{short_values:,}"
)


# ============================================================
# NON-PLAYER SEARCH CONTAMINATION
# ============================================================

section("NON-PLAYER SEARCH CONTAMINATION")


search_linked_to_entities = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search s
    INNER JOIN entities e
        ON s.reep_id = e.reep_id
    """
)


non_player_search_rows = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search s
    INNER JOIN entities e
        ON s.reep_id = e.reep_id
    WHERE e.entity_type <> 'player'
    """
)


player_search_rows = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search s
    INNER JOIN entities e
        ON s.reep_id = e.reep_id
    WHERE e.entity_type = 'player'
    """
)


print(
    f"  Search rows linked to entities : "
    f"{search_linked_to_entities:,}"
)

print(
    f"  Player search rows             : "
    f"{player_search_rows:,}"
)

print(
    f"  Non-player search rows         : "
    f"{non_player_search_rows:,}"
)


# ============================================================
# ORPHAN SEARCH RECORDS
# ============================================================

section("ORPHAN SEARCH RECORDS")


orphan_search_rows = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search s
    LEFT JOIN entities e
        ON s.reep_id = e.reep_id
    WHERE e.reep_id IS NULL
    """
)


print(
    f"  Search rows without entity : "
    f"{orphan_search_rows:,}"
)


# ============================================================
# SEARCH ENTITY TYPE CONSISTENCY
# ============================================================

section("SEARCH ENTITY TYPE CONSISTENCY")


mismatched_types = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search s
    INNER JOIN entities e
        ON s.reep_id = e.reep_id
    WHERE s.entity_type <> e.entity_type
    """
)


print(
    f"  Search/entity type mismatches : "
    f"{mismatched_types:,}"
)


# ============================================================
# SEARCH LABEL CONSISTENCY
# ============================================================

section("SEARCH LABEL CONSISTENCY")


label_mismatches = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search s
    INNER JOIN entities e
        ON s.reep_id = e.reep_id
    WHERE COALESCE(s.label, '')
          <> COALESCE(e.label, '')
    """
)


print(
    f"  Search/entity label mismatches : "
    f"{label_mismatches:,}"
)


# ============================================================
# BRIDGE / ALIAS SEARCH COVERAGE
# ============================================================

section("PLAYER BRIDGE / ALIAS SEARCH COVERAGE")


player_bridge_stats = con.execute(
    """
    SELECT

        COUNT(*) AS players,

        SUM(
            CASE
                WHEN COALESCE(s.bridge_count, 0) > 0
                THEN 1
                ELSE 0
            END
        ) AS with_bridges,

        SUM(
            CASE
                WHEN COALESCE(s.alias_count, 0) > 0
                THEN 1
                ELSE 0
            END
        ) AS with_aliases,

        SUM(
            CASE
                WHEN COALESCE(s.bridge_count, 0) = 0
                 AND COALESCE(s.alias_count, 0) = 0
                THEN 1
                ELSE 0
            END
        ) AS without_bridge_or_alias

    FROM players p

    LEFT JOIN entity_search s
        ON p.reep_id = s.reep_id
    """
).fetchone()


print(
    f"  Players                         : "
    f"{player_bridge_stats[0]:,}"
)

print(
    f"  Players with bridge evidence    : "
    f"{player_bridge_stats[1]:,}"
)

print(
    f"  Players with alias evidence     : "
    f"{player_bridge_stats[2]:,}"
)

print(
    f"  No bridge OR alias evidence     : "
    f"{player_bridge_stats[3]:,}"
)


# ============================================================
# SEARCH TEXT DISTINCTNESS
# ============================================================

section("SEARCH TEXT DISTINCTNESS")


total_search_values = safe_count(
    con,
    """
    SELECT COUNT(*)
    FROM entity_search
    WHERE search_text IS NOT NULL
    """
)


distinct_search_values = safe_count(
    con,
    """
    SELECT COUNT(DISTINCT search_text)
    FROM entity_search
    WHERE search_text IS NOT NULL
    """
)


print(
    f"  Non-null search rows       : "
    f"{total_search_values:,}"
)

print(
    f"  Distinct search values     : "
    f"{distinct_search_values:,}"
)


# ============================================================
# SAMPLE PLAYERS WITHOUT SEARCH
# ============================================================

section("SAMPLE PLAYERS WITHOUT SEARCH RECORDS")


rows = con.execute(
    """
    SELECT
        p.reep_id,
        p.label
    FROM players p
    LEFT JOIN entity_search s
        ON p.reep_id = s.reep_id
    WHERE s.reep_id IS NULL
    ORDER BY p.reep_id
    LIMIT 25
    """
).fetchall()


if rows:

    for reep_id, label in rows:

        print(
            f"  {reep_id} | {label}"
        )

else:

    print("  None found.")


# ============================================================
# SAMPLE ORPHAN SEARCH RECORDS
# ============================================================

section("SAMPLE ORPHAN SEARCH RECORDS")


rows = con.execute(
    """
    SELECT
        s.reep_id,
        s.entity_type,
        s.label,
        s.search_text
    FROM entity_search s
    LEFT JOIN entities e
        ON s.reep_id = e.reep_id
    WHERE e.reep_id IS NULL
    LIMIT 25
    """
).fetchall()


if rows:

    for reep_id, entity_type, label, search_text in rows:

        print(
            f"  {reep_id} | "
            f"{entity_type} | "
            f"{label} | "
            f"{search_text}"
        )

else:

    print("  None found.")


# ============================================================
# SAMPLE TYPE MISMATCHES
# ============================================================

section("SAMPLE ENTITY TYPE MISMATCHES")


rows = con.execute(
    """
    SELECT

        s.reep_id,

        e.entity_type AS entity_type,

        s.entity_type AS search_entity_type,

        e.label

    FROM entity_search s

    INNER JOIN entities e
        ON s.reep_id = e.reep_id

    WHERE s.entity_type <> e.entity_type

    LIMIT 25
    """
).fetchall()


if rows:

    for (
        reep_id,
        entity_type,
        search_entity_type,
        label
    ) in rows:

        print(
            f"  {reep_id} | "
            f"entity={entity_type} | "
            f"search={search_entity_type} | "
            f"{label}"
        )

else:

    print("  None found.")


# ============================================================
# SAMPLE LABEL MISMATCHES
# ============================================================

section("SAMPLE ENTITY LABEL MISMATCHES")


rows = con.execute(
    """
    SELECT

        s.reep_id,

        e.label AS entity_label,

        s.label AS search_label

    FROM entity_search s

    INNER JOIN entities e
        ON s.reep_id = e.reep_id

    WHERE COALESCE(s.label, '')
          <> COALESCE(e.label, '')

    LIMIT 25
    """
).fetchall()


if rows:

    for (
        reep_id,
        entity_label,
        search_label
    ) in rows:

        print(
            f"  {reep_id} | "
            f"entity={entity_label!r} | "
            f"search={search_label!r}"
        )

else:

    print("  None found.")


# ============================================================
# SAMPLE DUPLICATE SEARCH VALUES
# ============================================================

section("SAMPLE DUPLICATE SEARCH VALUES")


rows = con.execute(
    """
    SELECT

        reep_id,

        LOWER(
            TRIM(
                CAST(search_text AS VARCHAR)
            )
        ) AS search_value,

        COUNT(*) AS n

    FROM entity_search

    WHERE search_text IS NOT NULL

    GROUP BY

        reep_id,

        LOWER(
            TRIM(
                CAST(search_text AS VARCHAR)
            )
        )

    HAVING COUNT(*) > 1

    ORDER BY n DESC

    LIMIT 25
    """
).fetchall()


if rows:

    for reep_id, search_value, count in rows:

        print(
            f"  {reep_id} | "
            f"{search_value!r} | "
            f"{count} rows"
        )

else:

    print("  None found.")


# ============================================================
# FINAL STATUS
# ============================================================

section("SEARCH / INDEX AUDIT STATUS")

print()
print("READ-ONLY AUDIT COMPLETE.")
print()
print("No tables were created.")
print("No rows were inserted.")
print("No rows were updated.")
print("No rows were deleted.")
print()
print("The REEP source database was NOT modified.")
print()
print(
    "Review the results above before proceeding "
    "to PLAYER-TO-CLUB EVIDENCE QUALITY."
)
print()

con.close()

print("Database connection closed.")
print()
print("=" * 70)
print("END OF AUDIT")
print("=" * 70)