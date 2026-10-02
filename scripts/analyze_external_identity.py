from pathlib import Path
import json
import csv
import duckdb
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DB = (
    ROOT.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

MASTER_JSON = ROOT / "output" / "reep-player-master.json"

OUTPUT_JSON = ROOT / "output" / "reep-external-identity-analysis.json"
OUTPUT_CSV = ROOT / "output" / "reep-external-identity-analysis.csv"

print("=" * 70)
print("REEP EXTERNAL IDENTITY ANALYSIS")
print("=" * 70)

print("\nProject root:")
print(f"  {ROOT}")

print("\nSource database:")
print(f"  {SOURCE_DB}")

print("\nLoading REEP master players...")

with MASTER_JSON.open("r", encoding="utf-8") as f:
    players = json.load(f)

player_ids = {p["reep_id"] for p in players}

print(f"  Master players: {len(players):,}")
print(f"  Unique REEP IDs: {len(player_ids):,}")

print("\nOpening REEP database READ-ONLY...")

con = duckdb.connect(
    database=str(SOURCE_DB),
    read_only=True
)

print("  Database opened: READ-ONLY")

print("\nChecking required tables...")

tables = {
    row[0]
    for row in con.execute(
        "SHOW TABLES"
    ).fetchall()
}

required_tables = {
    "players",
    "overlay_links",
    "overlay_xids",
}

missing = required_tables - tables

if missing:
    raise RuntimeError(
        f"Required tables missing: {sorted(missing)}"
    )

print("  Required tables: OK")

print("\nAnalyzing QID links...")

qid_total = con.execute(
    """
    SELECT COUNT(*)
    FROM main.overlay_links
    """
).fetchone()[0]

qid_players = con.execute(
    """
    SELECT COUNT(DISTINCT reep_id)
    FROM main.overlay_links
    WHERE reep_id IS NOT NULL
      AND TRIM(reep_id) <> ''
    """
).fetchone()[0]

qid_distinct = con.execute(
    """
    SELECT COUNT(DISTINCT qid)
    FROM main.overlay_links
    WHERE qid IS NOT NULL
      AND TRIM(qid) <> ''
    """
).fetchone()[0]

qid_missing = con.execute(
    """
    SELECT COUNT(*)
    FROM main.overlay_links
    WHERE qid IS NULL
       OR TRIM(qid) = ''
    """
).fetchone()[0]

qid_collision_count = con.execute(
    """
    SELECT COUNT(*)
    FROM (
        SELECT qid
        FROM main.overlay_links
        WHERE qid IS NOT NULL
          AND TRIM(qid) <> ''
        GROUP BY qid
        HAVING COUNT(DISTINCT reep_id) > 1
    ) q
    """
).fetchone()[0]

print(f"  QID link rows:              {qid_total:,}")
print(f"  Players with QID links:     {qid_players:,}")
print(f"  Distinct QIDs:              {qid_distinct:,}")
print(f"  Missing/empty QIDs:         {qid_missing:,}")
print(f"  QID collision groups:       {qid_collision_count:,}")

print("\nQID confidence / DOB verification...")

qid_quality = con.execute(
    """
    SELECT
        confidence,
        dob_check,
        COUNT(*) AS links,
        COUNT(DISTINCT reep_id) AS players
    FROM main.overlay_links
    GROUP BY confidence, dob_check
    ORDER BY confidence DESC, dob_check
    """
).fetchall()

for row in qid_quality:
    print(
        f"  confidence={row[0]} | "
        f"dob_check={row[1]} | "
        f"links={row[2]:,} | "
        f"players={row[3]:,}"
    )

print("\nAnalyzing external IDs...")

xid_total = con.execute(
    """
    SELECT COUNT(*)
    FROM main.overlay_xids
    """
).fetchone()[0]

xid_players = con.execute(
    """
    SELECT COUNT(DISTINCT reep_id)
    FROM main.overlay_xids
    WHERE reep_id IS NOT NULL
      AND TRIM(reep_id) <> ''
    """
).fetchone()[0]

xid_distinct = con.execute(
    """
    SELECT COUNT(DISTINCT external_id)
    FROM main.overlay_xids
    WHERE external_id IS NOT NULL
      AND TRIM(external_id) <> ''
    """
).fetchone()[0]

xid_providers = con.execute(
    """
    SELECT COUNT(DISTINCT provider)
    FROM main.overlay_xids
    WHERE provider IS NOT NULL
      AND TRIM(provider) <> ''
    """
).fetchone()[0]

xid_missing = con.execute(
    """
    SELECT COUNT(*)
    FROM main.overlay_xids
    WHERE external_id IS NULL
       OR TRIM(external_id) = ''
    """
).fetchone()[0]

print(f"  External-ID rows:           {xid_total:,}")
print(f"  Players with external IDs:  {xid_players:,}")
print(f"  Distinct external IDs:      {xid_distinct:,}")
print(f"  Providers:                  {xid_providers:,}")
print(f"  Missing/empty external IDs: {xid_missing:,}")

print("\nExternal-ID provider distribution...")

provider_rows = con.execute(
    """
    SELECT
        provider,
        COUNT(*) AS rows,
        COUNT(DISTINCT reep_id) AS players,
        COUNT(DISTINCT external_id) AS external_ids
    FROM main.overlay_xids
    GROUP BY provider
    ORDER BY rows DESC, provider
    """
).fetchall()

for row in provider_rows:
    print(
        f"  {row[0]}: "
        f"rows={row[1]:,} | "
        f"players={row[2]:,} | "
        f"external_ids={row[3]:,}"
    )

print("\nComparing QID and external-ID player coverage...")

coverage = con.execute(
    """
    WITH q AS (
        SELECT DISTINCT reep_id
        FROM main.overlay_links
        WHERE reep_id IS NOT NULL
          AND TRIM(reep_id) <> ''
    ),
    x AS (
        SELECT DISTINCT reep_id
        FROM main.overlay_xids
        WHERE reep_id IS NOT NULL
          AND TRIM(reep_id) <> ''
    )
    SELECT
        (SELECT COUNT(*) FROM q) AS qid_players,
        (SELECT COUNT(*) FROM x) AS xid_players,
        (
            SELECT COUNT(*)
            FROM q
            INNER JOIN x USING (reep_id)
        ) AS both,
        (
            SELECT COUNT(*)
            FROM q
            LEFT JOIN x USING (reep_id)
            WHERE x.reep_id IS NULL
        ) AS qid_only,
        (
            SELECT COUNT(*)
            FROM x
            LEFT JOIN q USING (reep_id)
            WHERE q.reep_id IS NULL
        ) AS xid_only
    """
).fetchone()

print(f"  QID players:                {coverage[0]:,}")
print(f"  External-ID players:        {coverage[1]:,}")
print(f"  Players with both:          {coverage[2]:,}")
print(f"  QID-only players:           {coverage[3]:,}")
print(f"  External-ID-only players:   {coverage[4]:,}")

print("\nChecking coverage against REEP master...")

qid_outside_master = con.execute(
    """
    SELECT COUNT(DISTINCT ol.reep_id)
    FROM main.overlay_links ol
    LEFT JOIN main.players p
      ON p.reep_id = ol.reep_id
    WHERE ol.reep_id IS NOT NULL
      AND p.reep_id IS NULL
    """
).fetchone()[0]

xid_outside_master = con.execute(
    """
    SELECT COUNT(DISTINCT ox.reep_id)
    FROM main.overlay_xids ox
    LEFT JOIN main.players p
      ON p.reep_id = ox.reep_id
    WHERE ox.reep_id IS NOT NULL
      AND p.reep_id IS NULL
    """
).fetchone()[0]

print(f"  QID links outside master:   {qid_outside_master:,}")
print(f"  XID links outside master:   {xid_outside_master:,}")

print("\nBuilding provider summary...")

provider_summary = []

for provider, rows, provider_players, external_ids in provider_rows:
    provider_summary.append({
        "provider": provider,
        "rows": rows,
        "players": provider_players,
        "distinct_external_ids": external_ids,
    })

summary = {
    "total_master_players": len(players),
    "unique_master_reep_ids": len(player_ids),

    "qid": {
        "link_rows": qid_total,
        "players": qid_players,
        "distinct_qids": qid_distinct,
        "missing_or_empty_qids": qid_missing,
        "collision_groups": qid_collision_count,
        "quality_distribution": [
            {
                "confidence": row[0],
                "dob_check": row[1],
                "links": row[2],
                "players": row[3],
            }
            for row in qid_quality
        ],
    },

    "external_ids": {
        "rows": xid_total,
        "players": xid_players,
        "distinct_external_ids": xid_distinct,
        "providers": xid_providers,
        "missing_or_empty_external_ids": xid_missing,
        "provider_distribution": provider_summary,
    },

    "coverage": {
        "qid_players": coverage[0],
        "external_id_players": coverage[1],
        "both": coverage[2],
        "qid_only": coverage[3],
        "external_id_only": coverage[4],
        "qid_links_outside_master": qid_outside_master,
        "external_id_links_outside_master": xid_outside_master,
    },

    "players_merged": 0,
    "players_deleted": 0,
    "cross_database_matching_performed": False,
    "source_database_modified": False,
}

print("\nWriting analysis JSON...")

with OUTPUT_JSON.open("w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"  JSON written: {OUTPUT_JSON}")

print("\nWriting provider CSV...")

with OUTPUT_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "provider",
            "rows",
            "players",
            "distinct_external_ids",
        ],
    )

    writer.writeheader()
    writer.writerows(provider_summary)

print(f"  CSV written: {OUTPUT_CSV}")

con.close()

print("\n" + "=" * 70)
print("EXTERNAL IDENTITY ANALYSIS COMPLETE")
print("=" * 70)

print(f"\nREEP master players:          {len(players):,}")
print(f"Players with QID:             {qid_players:,}")
print(f"Players with external IDs:    {xid_players:,}")
print(f"Players with both:            {coverage[2]:,}")
print(f"QID collision groups:         {qid_collision_count:,}")
print(f"External-ID providers:        {xid_providers:,}")

print("\nPlayers merged:               0")
print("Players deleted:              0")
print("Cross-database matching:      NO")
print("Source database modified:     NO")

print("\nREEP IDs remain authoritative.")
print("The source DuckDB was opened READ-ONLY.")