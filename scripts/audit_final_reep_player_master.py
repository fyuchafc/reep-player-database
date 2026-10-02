import duckdb
import json
from pathlib import Path
from datetime import datetime


# ============================================================
# REEP FINAL PLAYER MASTER DATABASE AUDIT
# ============================================================
#
# READ-ONLY AUDIT
#
# This script DOES NOT modify the final database.
#
# It validates:
#   1. Required tables
#   2. Table schemas
#   3. Row counts
#   4. Player identity integrity
#   5. Field completeness
#   6. Gender distribution
#   7. Alias integrity
#   8. External-ID integrity
#   9. Provider / namespace coverage
#  10. Observed-club evidence
#  11. Metadata
#  12. Indexes
#  13. Expected build counts
#  14. Structural integrity
#  15. Final PASS / FAIL status
#
# Output:
#   output/reep-player-master-final-audit.json
#
# ============================================================


# ============================================================
# PATHS
# ============================================================

REPO_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = REPO_ROOT / "output" / "reep-player-master.duckdb"

OUTPUT_DIR = REPO_ROOT / "output"

AUDIT_PATH = OUTPUT_DIR / "reep-player-master-final-audit.json"


# ============================================================
# EXPECTED COUNTS FROM SUCCESSFUL BUILD
# ============================================================

EXPECTED = {
    "players": 432124,
    "aliases": 597522,
    "external_ids": 2789713,
    "observed_clubs": 142518,
}


# ============================================================
# REQUIRED TABLES
# ============================================================

REQUIRED_TABLES = [
    "players",
    "aliases",
    "external_ids",
    "observed_clubs",
    "database_metadata",
]


# ============================================================
# EXPECTED SCHEMAS
# ============================================================

EXPECTED_SCHEMAS = {
    "players": [
        "reep_id",
        "entity_type",
        "status",
        "label",
        "gender",
        "corroboration_grade",
        "corroboration_count",
        "source_tier_band",
    ],
    "aliases": [
        "reep_id",
        "alias",
        "kind",
        "rank",
        "language",
    ],
    "external_ids": [
        "provider",
        "namespace",
        "external_id",
        "reep_id",
        "rung",
    ],
    "observed_clubs": [
        "reep_id",
        "observed_clubs",
        "first_observed_season",
        "last_observed_season",
        "basis",
    ],
    "database_metadata": [
        "key",
        "value",
    ],
}


# ============================================================
# HELPERS
# ============================================================

def safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


def pct(part, total):
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def get_columns(con, table_name):
    rows = con.execute(
        f"PRAGMA table_info('{table_name}')"
    ).fetchall()

    return [row[1] for row in rows]


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

    return safe_int(row[0]) > 0


def count_rows(con, table_name):
    row = con.execute(
        f"SELECT COUNT(*) FROM main.{table_name}"
    ).fetchone()

    return safe_int(row[0])


def print_section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# START
# ============================================================

print("=" * 70)
print("REEP FINAL PLAYER MASTER DATABASE AUDIT")
print("=" * 70)
print()
print("READ-ONLY — final database will NOT be modified.")
print()
print("Database:")
print(DB_PATH)
print()

if not DB_PATH.exists():
    print("ERROR: Final REEP player master database was not found.")
    print()
    print("Expected:")
    print(DB_PATH)
    raise SystemExit(1)


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONNECT READ-ONLY
# ============================================================

print("Opening final REEP player master database READ-ONLY...")

con = duckdb.connect(
    str(DB_PATH),
    read_only=True,
)

print("Connected successfully.")


# ============================================================
# AUDIT RESULT STRUCTURE
# ============================================================

audit = {
    "audit_name": "REEP Final Player Master Database Audit",
    "audit_version": "1.0",
    "read_only": True,
    "database": str(DB_PATH),
    "audit_timestamp_utc": datetime.utcnow().isoformat() + "Z",
    "expected_counts": EXPECTED,
    "tables": {},
    "schemas": {},
    "players": {},
    "aliases": {},
    "external_ids": {},
    "observed_clubs": {},
    "metadata": {},
    "indexes": {},
    "validation": {},
    "final_status": "UNKNOWN",
}


overall_pass = True


# ============================================================
# 1. REQUIRED TABLES
# ============================================================

print_section("1. CHECKING REQUIRED TABLES")

table_status = {}

for table in REQUIRED_TABLES:
    exists = table_exists(con, table)

    table_status[table] = exists

    print(
        f"  {table:<20} "
        f"{'FOUND' if exists else 'MISSING'}"
    )

    if not exists:
        overall_pass = False


audit["tables"] = table_status


if not all(table_status.values()):
    print()
    print("ERROR: One or more required tables are missing.")
    audit["final_status"] = "FAIL"

    with open(AUDIT_PATH, "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)

    con.close()

    print()
    print("Audit report saved:")
    print(AUDIT_PATH)

    raise SystemExit(1)


# ============================================================
# 2. SCHEMA VALIDATION
# ============================================================

print_section("2. CHECKING TABLE SCHEMAS")

schema_results = {}

for table, expected_columns in EXPECTED_SCHEMAS.items():

    actual_columns = get_columns(con, table)

    exact_match = actual_columns == expected_columns

    schema_results[table] = {
        "expected": expected_columns,
        "actual": actual_columns,
        "exact_match": exact_match,
    }

    print()
    print(f"{table}")
    print(f"  Expected: {expected_columns}")
    print(f"  Actual:   {actual_columns}")
    print(
        f"  Status:   "
        f"{'PASS' if exact_match else 'FAIL'}"
    )

    if not exact_match:
        overall_pass = False


audit["schemas"] = schema_results


# ============================================================
# 3. TABLE COUNTS
# ============================================================

print_section("3. TABLE ROW COUNTS")

table_counts = {}

for table in REQUIRED_TABLES:
    count = count_rows(con, table)

    table_counts[table] = count

    print(f"  {table:<20} {count:,}")

audit["tables"]["row_counts"] = table_counts


# ============================================================
# 4. PLAYER MASTER IDENTITY
# ============================================================

print_section("4. PLAYER MASTER IDENTITY")

players_total = count_rows(con, "players")

duplicate_player_ids = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT reep_id
            FROM main.players
            GROUP BY reep_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
)

null_player_ids = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.players
        WHERE reep_id IS NULL
           OR TRIM(reep_id) = ''
        """
    ).fetchone()[0]
)

non_player_rows = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.players
        WHERE entity_type IS NULL
           OR LOWER(TRIM(entity_type)) <> 'player'
        """
    ).fetchone()[0]
)

null_labels = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.players
        WHERE label IS NULL
           OR TRIM(label) = ''
        """
    ).fetchone()[0]
)

null_status = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.players
        WHERE status IS NULL
           OR TRIM(status) = ''
        """
    ).fetchone()[0]
)

distinct_player_ids = safe_int(
    con.execute(
        """
        SELECT COUNT(DISTINCT reep_id)
        FROM main.players
        """
    ).fetchone()[0]
)


print(f"  Total players:              {players_total:,}")
print(f"  Distinct REEP IDs:          {distinct_player_ids:,}")
print(f"  Duplicate REEP IDs:         {duplicate_player_ids:,}")
print(f"  NULL/empty REEP IDs:        {null_player_ids:,}")
print(f"  Non-player rows:            {non_player_rows:,}")
print(f"  NULL/empty labels:          {null_labels:,}")
print(f"  NULL/empty status:          {null_status:,}")


audit["players"]["identity"] = {
    "total": players_total,
    "distinct_reep_ids": distinct_player_ids,
    "duplicate_reep_ids": duplicate_player_ids,
    "null_or_empty_reep_ids": null_player_ids,
    "non_player_rows": non_player_rows,
    "null_or_empty_labels": null_labels,
    "null_or_empty_status": null_status,
}


if (
    duplicate_player_ids > 0
    or null_player_ids > 0
    or non_player_rows > 0
    or null_labels > 0
    or null_status > 0
):
    overall_pass = False


# ============================================================
# 5. PLAYER FIELD COMPLETENESS
# ============================================================

print_section("5. PLAYER FIELD COMPLETENESS")

fields = [
    "reep_id",
    "entity_type",
    "status",
    "label",
    "gender",
    "corroboration_grade",
    "corroboration_count",
    "source_tier_band",
]

field_checks = {}

for field in fields:

    row = con.execute(
        f"""
        SELECT
            COUNT(*) AS total,
            COUNT({field}) AS populated,
            COUNT(*) - COUNT({field}) AS null_count,
            COUNT(DISTINCT {field}) AS distinct_values
        FROM main.players
        """
    ).fetchone()

    total = safe_int(row[0])
    populated = safe_int(row[1])
    null_count = safe_int(row[2])
    distinct_values = safe_int(row[3])

    null_or_empty = safe_int(
        con.execute(
            f"""
            SELECT COUNT(*)
            FROM main.players
            WHERE {field} IS NULL
               OR TRIM(CAST({field} AS VARCHAR)) = ''
            """
        ).fetchone()[0]
    )

    populated_pct = pct(populated, total)

    field_checks[field] = {
        "total": total,
        "populated": populated,
        "null_count": null_count,
        "null_or_empty": null_or_empty,
        "populated_percent": populated_pct,
        "distinct_values": distinct_values,
    }

    print()
    print(f"  {field}")
    print(f"    populated:     {populated:,}/{total:,} ({populated_pct}%)")
    print(f"    null:          {null_count:,}")
    print(f"    null/empty:    {null_or_empty:,}")
    print(f"    distinct:      {distinct_values:,}")


audit["players"]["field_completeness"] = field_checks


# Required identity fields must always be populated.
required_fields = [
    "reep_id",
    "entity_type",
    "status",
    "label",
]

for field in required_fields:
    if field_checks[field]["null_or_empty"] > 0:
        overall_pass = False


# ============================================================
# 6. GENDER DISTRIBUTION
# ============================================================

print_section("6. GENDER DISTRIBUTION")

gender_rows = con.execute(
    """
    SELECT
        COALESCE(NULLIF(TRIM(gender), ''), '[NULL/EMPTY]') AS gender,
        COUNT(*) AS count
    FROM main.players
    GROUP BY 1
    ORDER BY count DESC
    """
).fetchall()

gender_distribution = []

for gender, count in gender_rows:

    count = safe_int(count)

    gender_distribution.append(
        {
            "gender": gender,
            "count": count,
            "percent": pct(count, players_total),
        }
    )

    print(
        f"  {gender:<20} "
        f"{count:>10,} "
        f"({pct(count, players_total)}%)"
    )


audit["players"]["gender_distribution"] = gender_distribution


# ============================================================
# 7. CORROBORATION DISTRIBUTION
# ============================================================

print_section("7. CORROBORATION GRADE DISTRIBUTION")

corr_rows = con.execute(
    """
    SELECT
        COALESCE(
            NULLIF(TRIM(corroboration_grade), ''),
            '[NULL/EMPTY]'
        ) AS grade,
        COUNT(*) AS count
    FROM main.players
    GROUP BY 1
    ORDER BY count DESC
    """
).fetchall()

corroboration_distribution = []

for grade, count in corr_rows:

    count = safe_int(count)

    corroboration_distribution.append(
        {
            "grade": grade,
            "count": count,
            "percent": pct(count, players_total),
        }
    )

    print(
        f"  {grade:<20} "
        f"{count:>10,} "
        f"({pct(count, players_total)}%)"
    )


audit["players"]["corroboration_distribution"] = (
    corroboration_distribution
)


# ============================================================
# 8. ALIAS VALIDATION
# ============================================================

print_section("8. ALIAS VALIDATION")

aliases_total = count_rows(con, "aliases")

alias_players = safe_int(
    con.execute(
        """
        SELECT COUNT(DISTINCT p.reep_id)
        FROM main.players p
        INNER JOIN main.aliases a
            ON a.reep_id = p.reep_id
        """
    ).fetchone()[0]
)

alias_orphans = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.aliases a
        LEFT JOIN main.players p
            ON p.reep_id = a.reep_id
        WHERE p.reep_id IS NULL
        """
    ).fetchone()[0]
)

alias_null_ids = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.aliases
        WHERE reep_id IS NULL
           OR TRIM(reep_id) = ''
        """
    ).fetchone()[0]
)

alias_null_values = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.aliases
        WHERE alias IS NULL
           OR TRIM(alias) = ''
        """
    ).fetchone()[0]
)

duplicate_alias_rows = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                reep_id,
                alias,
                kind,
                rank,
                language
            FROM main.aliases
            GROUP BY
                reep_id,
                alias,
                kind,
                rank,
                language
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
)

players_without_aliases = players_total - alias_players


print(f"  Total alias rows:            {aliases_total:,}")
print(f"  Players with aliases:        {alias_players:,}")
print(f"  Players without aliases:     {players_without_aliases:,}")
print(f"  Orphan alias rows:           {alias_orphans:,}")
print(f"  NULL/empty player IDs:       {alias_null_ids:,}")
print(f"  NULL/empty alias values:     {alias_null_values:,}")
print(f"  Duplicate alias groups:      {duplicate_alias_rows:,}")


audit["aliases"] = {
    "total_rows": aliases_total,
    "players_with_aliases": alias_players,
    "players_without_aliases": players_without_aliases,
    "orphan_rows": alias_orphans,
    "null_or_empty_reep_ids": alias_null_ids,
    "null_or_empty_alias_values": alias_null_values,
    "duplicate_groups": duplicate_alias_rows,
}


if (
    alias_orphans > 0
    or alias_null_ids > 0
    or alias_null_values > 0
):
    overall_pass = False


# ============================================================
# 9. EXTERNAL-ID VALIDATION
# ============================================================

print_section("9. EXTERNAL-ID VALIDATION")

external_total = count_rows(con, "external_ids")

external_players = safe_int(
    con.execute(
        """
        SELECT COUNT(DISTINCT p.reep_id)
        FROM main.players p
        INNER JOIN main.external_ids e
            ON e.reep_id = p.reep_id
        """
    ).fetchone()[0]
)

external_orphans = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.external_ids e
        LEFT JOIN main.players p
            ON p.reep_id = e.reep_id
        WHERE p.reep_id IS NULL
        """
    ).fetchone()[0]
)

external_null_ids = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.external_ids
        WHERE reep_id IS NULL
           OR TRIM(reep_id) = ''
        """
    ).fetchone()[0]
)

external_null_external_ids = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.external_ids
        WHERE external_id IS NULL
           OR TRIM(external_id) = ''
        """
    ).fetchone()[0]
)

external_null_provider = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.external_ids
        WHERE provider IS NULL
           OR TRIM(provider) = ''
        """
    ).fetchone()[0]
)

external_null_namespace = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.external_ids
        WHERE namespace IS NULL
           OR TRIM(namespace) = ''
        """
    ).fetchone()[0]
)

duplicate_external_groups = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                provider,
                namespace,
                external_id,
                reep_id
            FROM main.external_ids
            GROUP BY
                provider,
                namespace,
                external_id,
                reep_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
)

players_without_external_ids = players_total - external_players


print(f"  Total external-ID rows:      {external_total:,}")
print(f"  Players with external IDs:   {external_players:,}")
print(f"  Players without external IDs:{players_without_external_ids:,}")
print(f"  Orphan rows:                 {external_orphans:,}")
print(f"  NULL/empty REEP IDs:         {external_null_ids:,}")
print(f"  NULL/empty external IDs:     {external_null_external_ids:,}")
print(f"  NULL/empty providers:        {external_null_provider:,}")
print(f"  NULL/empty namespaces:       {external_null_namespace:,}")
print(f"  Duplicate groups:            {duplicate_external_groups:,}")


audit["external_ids"] = {
    "total_rows": external_total,
    "players_with_external_ids": external_players,
    "players_without_external_ids": players_without_external_ids,
    "orphan_rows": external_orphans,
    "null_or_empty_reep_ids": external_null_ids,
    "null_or_empty_external_ids": external_null_external_ids,
    "null_or_empty_providers": external_null_provider,
    "null_or_empty_namespaces": external_null_namespace,
    "duplicate_groups": duplicate_external_groups,
}


if (
    external_orphans > 0
    or external_null_ids > 0
    or external_null_external_ids > 0
    or external_null_provider > 0
    or external_null_namespace > 0
):
    overall_pass = False


# ============================================================
# 10. PROVIDER DISTRIBUTION
# ============================================================

print_section("10. EXTERNAL-ID PROVIDER DISTRIBUTION")

provider_rows = con.execute(
    """
    SELECT
        COALESCE(NULLIF(TRIM(provider), ''), '[NULL/EMPTY]') AS provider,
        COUNT(*) AS count
    FROM main.external_ids
    GROUP BY 1
    ORDER BY count DESC
    """
).fetchall()

provider_distribution = []

for provider, count in provider_rows:

    count = safe_int(count)

    provider_distribution.append(
        {
            "provider": provider,
            "count": count,
            "percent": pct(count, external_total),
        }
    )

    print(
        f"  {provider:<30} "
        f"{count:>12,} "
        f"({pct(count, external_total)}%)"
    )


audit["external_ids"]["provider_distribution"] = (
    provider_distribution
)


# ============================================================
# 11. NAMESPACE DISTRIBUTION
# ============================================================

print_section("11. EXTERNAL-ID NAMESPACE DISTRIBUTION")

namespace_rows = con.execute(
    """
    SELECT
        COALESCE(NULLIF(TRIM(namespace), ''), '[NULL/EMPTY]')
            AS namespace,
        COUNT(*) AS count
    FROM main.external_ids
    GROUP BY 1
    ORDER BY count DESC
    """
).fetchall()

namespace_distribution = []

for namespace, count in namespace_rows:

    count = safe_int(count)

    namespace_distribution.append(
        {
            "namespace": namespace,
            "count": count,
            "percent": pct(count, external_total),
        }
    )

    print(
        f"  {namespace:<30} "
        f"{count:>12,} "
        f"({pct(count, external_total)}%)"
    )


audit["external_ids"]["namespace_distribution"] = (
    namespace_distribution
)


# ============================================================
# 12. OBSERVED CLUB EVIDENCE
# ============================================================

print_section("12. OBSERVED CLUB EVIDENCE")

clubs_total = count_rows(con, "observed_clubs")

club_players = safe_int(
    con.execute(
        """
        SELECT COUNT(DISTINCT p.reep_id)
        FROM main.players p
        INNER JOIN main.observed_clubs c
            ON c.reep_id = p.reep_id
        """
    ).fetchone()[0]
)

club_orphans = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.observed_clubs c
        LEFT JOIN main.players p
            ON p.reep_id = c.reep_id
        WHERE p.reep_id IS NULL
        """
    ).fetchone()[0]
)

club_non_player_rows = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.observed_clubs c
        WHERE EXISTS (
            SELECT 1
            FROM main.players p
            WHERE p.reep_id = c.reep_id
        )
        AND c.reep_id IS NULL
        """
    ).fetchone()[0]
)

club_null_ids = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.observed_clubs
        WHERE reep_id IS NULL
           OR TRIM(reep_id) = ''
        """
    ).fetchone()[0]
)

club_null_evidence = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM main.observed_clubs
        WHERE observed_clubs IS NULL
           OR TRIM(observed_clubs) = ''
        """
    ).fetchone()[0]
)

duplicate_club_player_ids = safe_int(
    con.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT reep_id
            FROM main.observed_clubs
            GROUP BY reep_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
)

basis_distribution_rows = con.execute(
    """
    SELECT
        COALESCE(NULLIF(TRIM(basis), ''), '[NULL/EMPTY]') AS basis,
        COUNT(*) AS count
    FROM main.observed_clubs
    GROUP BY 1
    ORDER BY count DESC
    """
).fetchall()

basis_distribution = []

for basis, count in basis_distribution_rows:

    count = safe_int(count)

    basis_distribution.append(
        {
            "basis": basis,
            "count": count,
            "percent": pct(count, clubs_total),
        }
    )

    print(
        f"  {basis[:55]:<55} "
        f"{count:>10,}"
    )


print()
print(f"  Total club evidence rows:    {clubs_total:,}")
print(f"  Players with club evidence:  {club_players:,}")
print(f"  Players without evidence:    {players_total - club_players:,}")
print(f"  Orphan club rows:             {club_orphans:,}")
print(f"  NULL/empty REEP IDs:          {club_null_ids:,}")
print(f"  NULL/empty club evidence:     {club_null_evidence:,}")
print(f"  Duplicate club player IDs:    {duplicate_club_player_ids:,}")


audit["observed_clubs"] = {
    "total_rows": clubs_total,
    "players_with_club_evidence": club_players,
    "players_without_club_evidence": players_total - club_players,
    "orphan_rows": club_orphans,
    "null_or_empty_reep_ids": club_null_ids,
    "null_or_empty_observed_clubs": club_null_evidence,
    "duplicate_player_ids": duplicate_club_player_ids,
    "basis_distribution": basis_distribution,
    "career_reconstruction": False,
    "limitation": (
        "Observed clubs represent clubs this person appears for "
        "in the register's own match coverage; they are not a "
        "complete career history."
    ),
}


if (
    club_orphans > 0
    or club_null_ids > 0
    or club_null_evidence > 0
    or duplicate_club_player_ids > 0
):
    overall_pass = False


# ============================================================
# 13. DATABASE METADATA
# ============================================================

print_section("13. DATABASE METADATA")

metadata_rows = con.execute(
    """
    SELECT key, value
    FROM main.database_metadata
    ORDER BY key
    """
).fetchall()

metadata = {}

for key, value in metadata_rows:

    metadata[str(key)] = value

    print(
        f"  {str(key):<30} "
        f"{value}"
    )


audit["metadata"] = metadata


# ============================================================
# 14. INDEX VALIDATION
# ============================================================

print_section("14. CHECKING INDEXES")

index_rows = con.execute(
    """
    SELECT
        index_name,
        table_name,
        sql
    FROM duckdb_indexes()
    WHERE schema_name = 'main'
    ORDER BY table_name, index_name
    """
).fetchall()

index_results = []

for index_name, table_name, sql in index_rows:

    index_results.append(
        {
            "index_name": index_name,
            "table_name": table_name,
            "sql": sql,
        }
    )

    print(
        f"  {index_name:<35} "
        f"{table_name}"
    )


audit["indexes"] = {
    "count": len(index_results),
    "indexes": index_results,
}


# ============================================================
# 15. EXPECTED BUILD COUNTS
# ============================================================

print_section("15. CHECKING EXPECTED BUILD COUNTS")

expected_count_results = {}

count_mapping = {
    "players": players_total,
    "aliases": aliases_total,
    "external_ids": external_total,
    "observed_clubs": clubs_total,
}

for table, expected_count in EXPECTED.items():

    actual_count = count_mapping[table]

    match = actual_count == expected_count

    expected_count_results[table] = {
        "expected": expected_count,
        "actual": actual_count,
        "match": match,
    }

    print(
        f"  {table:<20} "
        f"expected={expected_count:,} "
        f"actual={actual_count:,} "
        f"{'PASS' if match else 'FAIL'}"
    )

    if not match:
        overall_pass = False


audit["validation"]["expected_counts"] = expected_count_results


# ============================================================
# 16. STRUCTURAL VALIDATION
# ============================================================

print_section("16. STRUCTURAL VALIDATION")

structural_checks = {
    "players_table_exists": table_exists(con, "players"),
    "aliases_table_exists": table_exists(con, "aliases"),
    "external_ids_table_exists": table_exists(con, "external_ids"),
    "observed_clubs_table_exists": table_exists(con, "observed_clubs"),
    "metadata_table_exists": table_exists(con, "database_metadata"),
    "player_ids_unique": duplicate_player_ids == 0,
    "player_ids_not_null": null_player_ids == 0,
    "player_rows_are_players": non_player_rows == 0,
    "labels_present": field_checks["label"]["null_or_empty"] == 0,
    "status_present": field_checks["status"]["null_or_empty"] == 0,
    "alias_orphans_zero": alias_orphans == 0,
    "external_id_orphans_zero": external_orphans == 0,
    "club_orphans_zero": club_orphans == 0,
    "club_ids_not_null": club_null_ids == 0,
    "external_ids_not_null": external_null_external_ids == 0,
}

for check_name, passed in structural_checks.items():

    print(
        f"  {check_name:<35} "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:
        overall_pass = False


audit["validation"]["structural_checks"] = structural_checks


# ============================================================
# 17. FINAL VALIDATION
# ============================================================

print_section("17. FINAL VALIDATION")

final_checks = {
    "required_tables": all(table_status.values()),
    "schemas": all(
        result["exact_match"]
        for result in schema_results.values()
    ),
    "player_identity": (
        duplicate_player_ids == 0
        and null_player_ids == 0
        and non_player_rows == 0
    ),
    "required_player_fields": all(
        field_checks[field]["null_or_empty"] == 0
        for field in required_fields
    ),
    "aliases": (
        alias_orphans == 0
        and alias_null_ids == 0
        and alias_null_values == 0
    ),
    "external_ids": (
        external_orphans == 0
        and external_null_ids == 0
        and external_null_external_ids == 0
        and external_null_provider == 0
        and external_null_namespace == 0
    ),
    "observed_clubs": (
        club_orphans == 0
        and club_null_ids == 0
        and club_null_evidence == 0
        and duplicate_club_player_ids == 0
    ),
    "expected_counts": all(
        result["match"]
        for result in expected_count_results.values()
    ),
}


for check_name, passed in final_checks.items():

    print(
        f"  {check_name:<30} "
        f"{'PASS' if passed else 'FAIL'}"
    )

    if not passed:
        overall_pass = False


audit["validation"]["final_checks"] = final_checks


# ============================================================
# FINAL STATUS
# ============================================================

if overall_pass:
    final_status = "PASS"
else:
    final_status = "FAIL"


audit["final_status"] = final_status


# ============================================================
# SAVE REPORT
# ============================================================

with open(
    AUDIT_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        audit,
        f,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# CLOSE DATABASE
# ============================================================

con.close()


# ============================================================
# FINAL OUTPUT
# ============================================================

print()
print("=" * 70)
print("FINAL AUDIT RESULT")
print("=" * 70)

print()
print(f"  STATUS: {final_status}")

print()
print("Audit report saved:")
print(AUDIT_PATH)

print()

if final_status == "PASS":

    print("=" * 70)
    print("REEP PLAYER MASTER DATABASE PASSED FINAL VALIDATION")
    print("=" * 70)

    print()
    print("The final REEP player master database passed:")
    print("  - Table validation")
    print("  - Schema validation")
    print("  - Player identity validation")
    print("  - Required field validation")
    print("  - Alias validation")
    print("  - External-ID validation")
    print("  - Observed-club evidence validation")
    print("  - Expected-count validation")
    print("  - Structural validation")

else:

    print("=" * 70)
    print("REEP PLAYER MASTER DATABASE FAILED FINAL VALIDATION")
    print("=" * 70)

    print()
    print("Review the audit report for the failed checks:")
    print(AUDIT_PATH)

print()