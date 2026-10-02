import duckdb
import json
from pathlib import Path

# ============================================================
# REEP OBSERVED CLUB ENTITY-TYPE DIAGNOSTIC
# ============================================================
# READ-ONLY
# Investigates unexpected entity_type values in observed_clubs.
# ============================================================

SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

OUTPUT_JSON = OUTPUT_DIR / "reep-observed-club-entity-type-diagnostic.json"

print("=" * 70)
print("REEP OBSERVED CLUB ENTITY-TYPE DIAGNOSTIC")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()
print(f"Source database:")
print(SOURCE_DB)
print()

if not SOURCE_DB.exists():
    print("ERROR: Source database not found.")
    raise SystemExit(1)

con = duckdb.connect(
    database=str(SOURCE_DB),
    read_only=True
)

print("Connected successfully.")
print()

# ------------------------------------------------------------
# 1. TOTAL ROWS
# ------------------------------------------------------------

total_rows = con.execute(
    "SELECT COUNT(*) FROM observed_clubs"
).fetchone()[0]

print("=" * 70)
print("TOTAL OBSERVED_CLUBS ROWS")
print("=" * 70)
print(f"  {total_rows:,}")
print()

# ------------------------------------------------------------
# 2. EXACT ENTITY TYPE DISTRIBUTION
# ------------------------------------------------------------

print("=" * 70)
print("EXACT ENTITY_TYPE DISTRIBUTION")
print("=" * 70)

rows = con.execute(
    """
    SELECT
        entity_type,
        COUNT(*) AS row_count
    FROM observed_clubs
    GROUP BY entity_type
    ORDER BY row_count DESC
    """
).fetchall()

entity_type_distribution = []

for entity_type, count in rows:
    value = entity_type if entity_type is not None else "<NULL>"

    print(
        f"  {value:<25} {count:,}"
    )

    entity_type_distribution.append({
        "entity_type": entity_type,
        "row_count": count
    })

print()

# ------------------------------------------------------------
# 3. NULL / EMPTY / NON-PLAYER
# ------------------------------------------------------------

null_count = con.execute(
    """
    SELECT COUNT(*)
    FROM observed_clubs
    WHERE entity_type IS NULL
    """
).fetchone()[0]

empty_count = con.execute(
    """
    SELECT COUNT(*)
    FROM observed_clubs
    WHERE TRIM(entity_type) = ''
    """
).fetchone()[0]

non_player_count = con.execute(
    """
    SELECT COUNT(*)
    FROM observed_clubs
    WHERE entity_type IS NOT NULL
      AND TRIM(entity_type) <> ''
      AND entity_type <> 'player'
    """
).fetchone()[0]

print("=" * 70)
print("ENTITY_TYPE QUALITY")
print("=" * 70)

print(f"  NULL entity_type:        {null_count:,}")
print(f"  Empty entity_type:       {empty_count:,}")
print(f"  Non-player entity_type:  {non_player_count:,}")
print()

# ------------------------------------------------------------
# 4. REEP ID VALIDITY
# ------------------------------------------------------------

print("=" * 70)
print("REEP ID VALIDITY")
print("=" * 70)

missing_reep_id = con.execute(
    """
    SELECT COUNT(*)
    FROM observed_clubs
    WHERE reep_id IS NULL
       OR TRIM(reep_id) = ''
    """
).fetchone()[0]

unknown_player_ids = con.execute(
    """
    SELECT COUNT(*)
    FROM observed_clubs oc
    LEFT JOIN players p
      ON p.reep_id = oc.reep_id
    WHERE p.reep_id IS NULL
    """
).fetchone()[0]

print(f"  Missing/empty REEP IDs:       {missing_reep_id:,}")
print(f"  REEP IDs not in players:      {unknown_player_ids:,}")
print()

# ------------------------------------------------------------
# 5. NON-PLAYER ENTITY TYPE SAMPLES
# ------------------------------------------------------------

print("=" * 70)
print("SAMPLES OF NON-PLAYER ENTITY TYPES")
print("=" * 70)

samples = con.execute(
    """
    SELECT
        reep_id,
        entity_type,
        observed_clubs,
        first_observed_season,
        last_observed_season,
        basis
    FROM observed_clubs
    WHERE entity_type IS NOT NULL
      AND TRIM(entity_type) <> ''
      AND entity_type <> 'player'
    ORDER BY entity_type, reep_id
    LIMIT 50
    """
).fetchall()

sample_rows = []

if samples:
    for row in samples:
        print(
            f"  reep_id={row[0]} | "
            f"entity_type={row[1]} | "
            f"observed_clubs={row[2]} | "
            f"first={row[3]} | "
            f"last={row[4]}"
        )

        sample_rows.append({
            "reep_id": row[0],
            "entity_type": row[1],
            "observed_clubs": row[2],
            "first_observed_season": row[3],
            "last_observed_season": row[4],
            "basis": row[5]
        })
else:
    print("  No non-player entity types found.")

print()

# ------------------------------------------------------------
# 6. CHECK WHETHER NON-PLAYER TYPES ACTUALLY BELONG TO PLAYERS
# ------------------------------------------------------------

print("=" * 70)
print("NON-PLAYER TYPE VS PLAYERS TABLE")
print("=" * 70)

joined_distribution = con.execute(
    """
    SELECT
        oc.entity_type,
        COUNT(*) AS rows_total,
        COUNT(p.reep_id) AS rows_matching_player,
        COUNT(*) - COUNT(p.reep_id) AS rows_not_matching_player
    FROM observed_clubs oc
    LEFT JOIN players p
      ON p.reep_id = oc.reep_id
    WHERE oc.entity_type IS NOT NULL
      AND TRIM(oc.entity_type) <> ''
      AND oc.entity_type <> 'player'
    GROUP BY oc.entity_type
    ORDER BY rows_total DESC
    """
).fetchall()

joined_rows = []

if joined_distribution:
    for row in joined_distribution:
        print(
            f"  {row[0]:<20} "
            f"total={row[1]:,} | "
            f"matching_player={row[2]:,} | "
            f"not_player={row[3]:,}"
        )

        joined_rows.append({
            "entity_type": row[0],
            "rows_total": row[1],
            "rows_matching_player": row[2],
            "rows_not_matching_player": row[3]
        })
else:
    print("  None.")

print()

# ------------------------------------------------------------
# 7. DUPLICATE REEP IDS
# ------------------------------------------------------------

print("=" * 70)
print("OBSERVED_CLUBS REEP-ID DUPLICATION")
print("=" * 70)

duplicate_groups = con.execute(
    """
    SELECT COUNT(*)
    FROM (
        SELECT reep_id
        FROM observed_clubs
        GROUP BY reep_id
        HAVING COUNT(*) > 1
    )
    """
).fetchone()[0]

extra_rows = con.execute(
    """
    SELECT
        COUNT(*) - COUNT(DISTINCT reep_id)
    FROM observed_clubs
    WHERE reep_id IS NOT NULL
    """
).fetchone()[0]

print(f"  REEP IDs appearing more than once: {duplicate_groups:,}")
print(f"  Extra rows beyond unique REEP IDs: {extra_rows:,}")
print()

# ------------------------------------------------------------
# 8. BASIS CONSISTENCY
# ------------------------------------------------------------

print("=" * 70)
print("BASIS VALUES")
print("=" * 70)

basis_rows = con.execute(
    """
    SELECT
        basis,
        COUNT(*) AS row_count
    FROM observed_clubs
    GROUP BY basis
    ORDER BY row_count DESC
    """
).fetchall()

basis_distribution = []

for basis, count in basis_rows:
    value = basis if basis is not None else "<NULL>"

    print(
        f"  {value}: {count:,}"
    )

    basis_distribution.append({
        "basis": basis,
        "row_count": count
    })

print()

# ------------------------------------------------------------
# SAVE REPORT
# ------------------------------------------------------------

report = {
    "audit": {
        "name": "REEP Observed Club Entity-Type Diagnostic",
        "read_only": True,
        "source_database": str(SOURCE_DB),
        "source_file_size_bytes": SOURCE_DB.stat().st_size
    },
    "total_rows": total_rows,
    "entity_type_distribution": entity_type_distribution,
    "entity_type_quality": {
        "null_count": null_count,
        "empty_count": empty_count,
        "non_player_count": non_player_count
    },
    "reep_id_validity": {
        "missing_or_empty": missing_reep_id,
        "unknown_player_ids": unknown_player_ids
    },
    "non_player_samples": sample_rows,
    "non_player_vs_players": joined_rows,
    "duplicate_analysis": {
        "duplicate_groups": duplicate_groups,
        "extra_rows": extra_rows
    },
    "basis_distribution": basis_distribution
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
print("DIAGNOSTIC COMPLETE")
print("=" * 70)
print()
print(f"Saved report:")
print(OUTPUT_JSON)
print()
print("SOURCE DATABASE WAS NOT MODIFIED.")