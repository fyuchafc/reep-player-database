import duckdb
import json
from pathlib import Path

# ============================================================
# REEP FINAL PLAYER SCHEMA AUDIT
# ============================================================
# READ-ONLY
#
# Purpose:
# Determine the exact fields available for the final
# REEP-only player master database.
#
# The source REEP database is NEVER modified.
# ============================================================

SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_JSON = OUTPUT_DIR / "reep-final-player-schema-audit.json"

print("=" * 70)
print("REEP FINAL PLAYER SCHEMA AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()
print(f"Source database:")
print(SOURCE_DB)
print()

if not SOURCE_DB.exists():
    print("ERROR: Source database was not found.")
    raise SystemExit(1)

print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=str(SOURCE_DB),
    read_only=True
)

print("Connected successfully.")
print()

# ------------------------------------------------------------
# REQUIRED TABLES
# ------------------------------------------------------------

required_tables = [
    "players",
    "entities",
    "entity_search",
    "aliases",
    "overlay_aliases",
    "bridges",
    "observed_clubs",
]

print("=" * 70)
print("CHECKING REQUIRED TABLES")
print("=" * 70)

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

table_status = {}

for table in required_tables:
    found = table in existing_tables
    table_status[table] = found
    print(f"  {table:<20} {'FOUND' if found else 'MISSING'}")

print()

# ------------------------------------------------------------
# HELPER
# ------------------------------------------------------------

def safe_count(sql, params=None):
    try:
        if params:
            return con.execute(sql, params).fetchone()[0]
        return con.execute(sql).fetchone()[0]
    except Exception:
        return None


def get_columns(table):
    try:
        rows = con.execute(
            """
            SELECT
                column_name,
                data_type,
                ordinal_position
            FROM information_schema.columns
            WHERE table_schema = 'main'
              AND table_name = ?
            ORDER BY ordinal_position
            """,
            [table],
        ).fetchall()

        return [
            {
                "column_name": r[0],
                "data_type": r[1],
                "ordinal_position": r[2],
            }
            for r in rows
        ]

    except Exception:
        return []


def get_table_count(table):
    try:
        return con.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]
    except Exception:
        return None


# ------------------------------------------------------------
# TABLE COUNTS
# ------------------------------------------------------------

print("=" * 70)
print("TABLE COUNTS")
print("=" * 70)

table_counts = {}

for table in required_tables:
    if table_status[table]:
        count = get_table_count(table)
        table_counts[table] = count
        print(f"  {table:<20} {count:,}")

print()

# ------------------------------------------------------------
# PLAYER MASTER COLUMNS
# ------------------------------------------------------------

print("=" * 70)
print("PLAYERS TABLE — EXACT COLUMNS")
print("=" * 70)

players_columns = get_columns("players")

for col in players_columns:
    print(
        f"  {col['ordinal_position']:>2}. "
        f"{col['column_name']:<30} "
        f"{col['data_type']}"
    )

print()

# ------------------------------------------------------------
# ENTITY COLUMNS
# ------------------------------------------------------------

print("=" * 70)
print("ENTITIES TABLE — EXACT COLUMNS")
print("=" * 70)

entities_columns = get_columns("entities")

for col in entities_columns:
    print(
        f"  {col['ordinal_position']:>2}. "
        f"{col['column_name']:<30} "
        f"{col['data_type']}"
    )

print()

# ------------------------------------------------------------
# ALIAS COLUMNS
# ------------------------------------------------------------

print("=" * 70)
print("ALIASES TABLE — EXACT COLUMNS")
print("=" * 70)

aliases_columns = get_columns("aliases")

for col in aliases_columns:
    print(
        f"  {col['ordinal_position']:>2}. "
        f"{col['column_name']:<30} "
        f"{col['data_type']}"
    )

print()

# ------------------------------------------------------------
# BRIDGE COLUMNS
# ------------------------------------------------------------

print("=" * 70)
print("BRIDGES TABLE — EXACT COLUMNS")
print("=" * 70)

bridges_columns = get_columns("bridges")

for col in bridges_columns:
    print(
        f"  {col['ordinal_position']:>2}. "
        f"{col['column_name']:<30} "
        f"{col['data_type']}"
    )

print()

# ------------------------------------------------------------
# OBSERVED CLUB COLUMNS
# ------------------------------------------------------------

print("=" * 70)
print("OBSERVED_CLUBS TABLE — EXACT COLUMNS")
print("=" * 70)

observed_clubs_columns = get_columns("observed_clubs")

for col in observed_clubs_columns:
    print(
        f"  {col['ordinal_position']:>2}. "
        f"{col['column_name']:<30} "
        f"{col['data_type']}"
    )

print()

# ------------------------------------------------------------
# PLAYER FIELD COMPLETENESS
# ------------------------------------------------------------

print("=" * 70)
print("PLAYER FIELD COMPLETENESS")
print("=" * 70)

player_field_stats = {}

if table_status["players"]:

    player_count = table_counts["players"]

    for col in players_columns:

        name = col["column_name"]

        try:
            row = con.execute(
                f'''
                SELECT
                    COUNT(*) AS total,
                    COUNT("{name}") AS populated,
                    COUNT(*) - COUNT("{name}") AS null_count,
                    COUNT(DISTINCT "{name}") AS distinct_count
                FROM players
                '''
            ).fetchone()

            total = row[0]
            populated = row[1]
            null_count = row[2]
            distinct_count = row[3]

            percentage = (
                (populated / total) * 100
                if total else 0
            )

            player_field_stats[name] = {
                "data_type": col["data_type"],
                "total_rows": total,
                "populated_rows": populated,
                "null_rows": null_count,
                "population_percent": round(percentage, 4),
                "distinct_values": distinct_count,
            }

            print(
                f"  {name:<30} "
                f"populated={populated:,} "
                f"null={null_count:,} "
                f"distinct={distinct_count:,} "
                f"coverage={percentage:.2f}%"
            )

        except Exception as e:

            player_field_stats[name] = {
                "error": str(e)
            }

            print(
                f"  {name:<30} ERROR: {e}"
            )

print()

# ------------------------------------------------------------
# PLAYER IDENTITY CONSISTENCY
# ------------------------------------------------------------

print("=" * 70)
print("PLAYER IDENTITY CONSISTENCY")
print("=" * 70)

identity_checks = {}

if table_status["players"] and table_status["entities"]:

    players_not_entities = safe_count(
        """
        SELECT COUNT(*)
        FROM players p
        LEFT JOIN entities e
          ON e.reep_id = p.reep_id
        WHERE e.reep_id IS NULL
        """
    )

    entities_not_players = safe_count(
        """
        SELECT COUNT(*)
        FROM entities e
        LEFT JOIN players p
          ON p.reep_id = e.reep_id
        WHERE e.entity_type = 'player'
          AND p.reep_id IS NULL
        """
    )

    non_player_rows_in_players = safe_count(
        """
        SELECT COUNT(*)
        FROM players p
        JOIN entities e
          ON e.reep_id = p.reep_id
        WHERE e.entity_type <> 'player'
        """
    )

    duplicate_player_ids = safe_count(
        """
        SELECT COUNT(*)
        FROM (
            SELECT reep_id
            FROM players
            GROUP BY reep_id
            HAVING COUNT(*) > 1
        )
        """
    )

    identity_checks = {
        "players_not_in_entities": players_not_entities,
        "player_entities_not_in_players": entities_not_players,
        "non_player_entities_inside_players": non_player_rows_in_players,
        "duplicate_player_ids": duplicate_player_ids,
    }

    print(
        f"  Players missing from entities: "
        f"{players_not_entities:,}"
    )

    print(
        f"  Player entities missing from players: "
        f"{entities_not_players:,}"
    )

    print(
        f"  Non-player entities inside players: "
        f"{non_player_rows_in_players:,}"
    )

    print(
        f"  Duplicate player IDs: "
        f"{duplicate_player_ids:,}"
    )

print()

# ------------------------------------------------------------
# ALIAS COVERAGE
# ------------------------------------------------------------

print("=" * 70)
print("PLAYER ALIAS COVERAGE")
print("=" * 70)

alias_stats = {}

if table_status["players"] and table_status["aliases"]:

    players_with_aliases = safe_count(
        """
        SELECT COUNT(DISTINCT p.reep_id)
        FROM players p
        JOIN aliases a
          ON a.reep_id = p.reep_id
        """
    )

    alias_rows_for_players = safe_count(
        """
        SELECT COUNT(*)
        FROM aliases a
        JOIN players p
          ON p.reep_id = a.reep_id
        """
    )

    players_without_aliases = safe_count(
        """
        SELECT COUNT(*)
        FROM players p
        LEFT JOIN aliases a
          ON a.reep_id = p.reep_id
        WHERE a.reep_id IS NULL
        """
    )

    alias_stats = {
        "players_with_aliases": players_with_aliases,
        "players_without_aliases": players_without_aliases,
        "alias_rows_for_players": alias_rows_for_players,
    }

    print(
        f"  Players with aliases: "
        f"{players_with_aliases:,}"
    )

    print(
        f"  Players without aliases: "
        f"{players_without_aliases:,}"
    )

    print(
        f"  Alias rows belonging to players: "
        f"{alias_rows_for_players:,}"
    )

print()

# ------------------------------------------------------------
# BRIDGE COVERAGE
# ------------------------------------------------------------

print("=" * 70)
print("PLAYER BRIDGE COVERAGE")
print("=" * 70)

bridge_stats = {}

if table_status["players"] and table_status["bridges"]:

    try:

        bridge_columns = {
            c["column_name"]
            for c in get_columns("bridges")
        }

        if "reep_id" in bridge_columns:

            players_with_bridges = safe_count(
                """
                SELECT COUNT(DISTINCT p.reep_id)
                FROM players p
                JOIN bridges b
                  ON b.reep_id = p.reep_id
                """
            )

            bridge_rows_for_players = safe_count(
                """
                SELECT COUNT(*)
                FROM bridges b
                JOIN players p
                  ON p.reep_id = b.reep_id
                """
            )

            bridge_stats = {
                "players_with_bridges": players_with_bridges,
                "bridge_rows_for_players": bridge_rows_for_players,
            }

            print(
                f"  Players with bridges: "
                f"{players_with_bridges:,}"
            )

            print(
                f"  Bridge rows belonging to players: "
                f"{bridge_rows_for_players:,}"
            )

        else:

            print(
                "  NOTE: bridges table does not use "
                "a direct reep_id column."
            )

            bridge_stats = {
                "note": "No direct reep_id column detected."
            }

    except Exception as e:

        print(f"  Bridge inspection error: {e}")

print()

# ------------------------------------------------------------
# CLUB EVIDENCE COVERAGE
# ------------------------------------------------------------

print("=" * 70)
print("PLAYER CLUB EVIDENCE COVERAGE")
print("=" * 70)

club_stats = {}

if table_status["players"] and table_status["observed_clubs"]:

    players_with_clubs = safe_count(
        """
        SELECT COUNT(DISTINCT p.reep_id)
        FROM players p
        JOIN observed_clubs oc
          ON oc.reep_id = p.reep_id
        """
    )

    players_without_clubs = safe_count(
        """
        SELECT COUNT(*)
        FROM players p
        LEFT JOIN observed_clubs oc
          ON oc.reep_id = p.reep_id
        WHERE oc.reep_id IS NULL
        """
    )

    invalid_club_entity_types = safe_count(
        """
        SELECT COUNT(*)
        FROM observed_clubs
        WHERE entity_type <> 'player'
        """
    )

    club_stats = {
        "players_with_observed_clubs": players_with_clubs,
        "players_without_observed_clubs": players_without_clubs,
        "invalid_observed_club_entity_types": invalid_club_entity_types,
    }

    print(
        f"  Players with observed-club evidence: "
        f"{players_with_clubs:,}"
    )

    print(
        f"  Players without observed-club evidence: "
        f"{players_without_clubs:,}"
    )

    print(
        f"  Invalid observed_club entity types: "
        f"{invalid_club_entity_types:,}"
    )

print()

# ------------------------------------------------------------
# FINAL SCHEMA RECOMMENDATION
# ------------------------------------------------------------

print("=" * 70)
print("PROPOSED FINAL PLAYER SCHEMA")
print("=" * 70)

proposed_schema = [
    {
        "field": "reep_id",
        "category": "identity",
        "required": True,
        "reason": "Canonical REEP player identifier",
    },
    {
        "field": "label",
        "category": "identity",
        "required": True,
        "reason": "Primary REEP player name",
    },
    {
        "field": "status",
        "category": "identity",
        "required": True,
        "reason": "REEP identity status",
    },
    {
        "field": "entity_type",
        "category": "identity",
        "required": True,
        "reason": "Must be player in player-only master",
    },
    {
        "field": "gender",
        "category": "identity",
        "required": False,
        "reason": "Available REEP player field",
    },
    {
        "field": "country",
        "category": "identity",
        "required": False,
        "reason": "Available REEP player field",
    },
    {
        "field": "aliases",
        "category": "identity",
        "required": False,
        "reason": "Preserve alternate names",
    },
    {
        "field": "qid",
        "category": "external_identity",
        "required": False,
        "reason": "Retain verified external identity linkage",
    },
    {
        "field": "external_ids",
        "category": "external_identity",
        "required": False,
        "reason": "Retain verified external identifiers",
    },
    {
        "field": "observed_clubs",
        "category": "club_evidence",
        "required": False,
        "reason": "Observed register match coverage only",
    },
    {
        "field": "first_observed_season",
        "category": "club_evidence",
        "required": False,
        "reason": "First season observed in register coverage",
    },
    {
        "field": "last_observed_season",
        "category": "club_evidence",
        "required": False,
        "reason": "Last season observed in register coverage",
    },
    {
        "field": "club_evidence_basis",
        "category": "club_evidence",
        "required": False,
        "reason": "Explicitly documents evidence limitation",
    },
    {
        "field": "corroboration_grade",
        "category": "provenance",
        "required": False,
        "reason": "REEP evidence quality grade",
    },
    {
        "field": "corroboration_count",
        "category": "provenance",
        "required": False,
        "reason": "REEP corroboration count",
    },
    {
        "field": "source_tier_band",
        "category": "provenance",
        "required": False,
        "reason": "REEP source tier information",
    },
]

for item in proposed_schema:
    req = "REQUIRED" if item["required"] else "OPTIONAL"

    print(
        f"  {item['field']:<28} "
        f"{item['category']:<20} "
        f"{req:<9} "
        f"{item['reason']}"
    )

print()

# ------------------------------------------------------------
# SAVE REPORT
# ------------------------------------------------------------

report = {
    "audit": {
        "name": "REEP Final Player Schema Audit",
        "read_only": True,
        "source_database": str(SOURCE_DB),
        "source_file_size_bytes": SOURCE_DB.stat().st_size,
    },
    "table_status": table_status,
    "table_counts": table_counts,
    "players_columns": players_columns,
    "entities_columns": entities_columns,
    "aliases_columns": aliases_columns,
    "bridges_columns": bridges_columns,
    "observed_clubs_columns": observed_clubs_columns,
    "player_field_stats": player_field_stats,
    "identity_checks": identity_checks,
    "alias_stats": alias_stats,
    "bridge_stats": bridge_stats,
    "club_stats": club_stats,
    "proposed_schema": proposed_schema,
}

with open(
    OUTPUT_JSON,
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        report,
        f,
        indent=2,
        ensure_ascii=False
    )

con.close()

print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
print()
print(f"Saved report:")
print(OUTPUT_JSON)
print()
print("SOURCE DATABASE WAS NOT MODIFIED.")