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

OUTPUT_JSON = ROOT / "output" / "reep-qid-collision-audit.json"
OUTPUT_CSV = ROOT / "output" / "reep-qid-collisions.csv"

print("=" * 70)
print("REEP QID COLLISION AUDIT")
print("=" * 70)

print("\nSource database:")
print(f"  {SOURCE_DB}")

print("\nOpening REEP database READ-ONLY...")

con = duckdb.connect(
    database=str(SOURCE_DB),
    read_only=True
)

print("  Database opened: READ-ONLY")

print("\nFinding QIDs linked to multiple REEP IDs...")

collision_rows = con.execute(
    """
    WITH collisions AS (
        SELECT
            qid,
            COUNT(*) AS link_rows,
            COUNT(DISTINCT reep_id) AS reep_players
        FROM main.overlay_links
        WHERE qid IS NOT NULL
          AND TRIM(qid) <> ''
        GROUP BY qid
        HAVING COUNT(DISTINCT reep_id) > 1
    )
    SELECT
        qid,
        link_rows,
        reep_players
    FROM collisions
    ORDER BY reep_players DESC, link_rows DESC, qid
    """
).fetchall()

print(f"  Collision QIDs: {len(collision_rows):,}")

print("\nLoading detailed collision records...")

details = con.execute(
    """
    WITH collisions AS (
        SELECT qid
        FROM main.overlay_links
        WHERE qid IS NOT NULL
          AND TRIM(qid) <> ''
        GROUP BY qid
        HAVING COUNT(DISTINCT reep_id) > 1
    )
    SELECT
        ol.qid,
        ol.reep_id,
        p.label,
        p.status,
        p.gender,
        ol.confidence,
        ol.dob_check,
        ol.entity_type,
        ol.inherited_count,
        ol.inherited
    FROM main.overlay_links ol
    INNER JOIN collisions c
        ON c.qid = ol.qid
    LEFT JOIN main.players p
        ON p.reep_id = ol.reep_id
    ORDER BY
        ol.qid,
        ol.reep_id
    """
).fetchall()

print(f"  Detailed collision rows: {len(details):,}")

print("\nAnalyzing collision characteristics...")

confidence_counts = Counter()
dob_counts = Counter()
entity_type_counts = Counter()
inherited_counts = Counter()
missing_player_counts = Counter()

for row in details:
    (
        qid,
        reep_id,
        label,
        status,
        gender,
        confidence,
        dob_check,
        entity_type,
        inherited_count,
        inherited,
    ) = row

    confidence_counts[str(confidence)] += 1
    dob_counts[str(dob_check)] += 1
    entity_type_counts[str(entity_type)] += 1
    inherited_counts[str(inherited)] += 1

    if label is None:
        missing_player_counts["missing_from_players"] += 1
    else:
        missing_player_counts["present_in_players"] += 1

print("\nConfidence distribution:")
for key, value in sorted(confidence_counts.items()):
    print(f"  {key}: {value:,}")

print("\nDOB-check distribution:")
for key, value in sorted(dob_counts.items()):
    print(f"  {key}: {value:,}")

print("\nEntity-type distribution:")
for key, value in sorted(entity_type_counts.items()):
    print(f"  {key}: {value:,}")

print("\nInherited distribution:")
for key, value in sorted(inherited_counts.items()):
    print(f"  {key}: {value:,}")

print("\nPlayer-table coverage:")
for key, value in sorted(missing_player_counts.items()):
    print(f"  {key}: {value:,}")

print("\nLargest collision groups:")

for qid, link_rows, reep_players in collision_rows[:20]:
    print(
        f"\n  {qid}  "
        f"({reep_players} REEP players, {link_rows} link rows)"
    )

    for row in details:
        if row[0] == qid:
            (
                _qid,
                reep_id,
                label,
                status,
                gender,
                confidence,
                dob_check,
                entity_type,
                inherited_count,
                inherited,
            ) = row

            label_text = label if label is not None else "NULL"

            print(
                f"    {reep_id} | "
                f"{label_text} | "
                f"{status} | "
                f"{gender} | "
                f"confidence={confidence} | "
                f"dob={dob_check} | "
                f"inherited={inherited}"
            )

print("\nWriting detailed CSV...")

with OUTPUT_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "qid",
        "reep_id",
        "label",
        "status",
        "gender",
        "confidence",
        "dob_check",
        "entity_type",
        "inherited_count",
        "inherited",
    ])

    writer.writerows(details)

print(f"  CSV written: {OUTPUT_CSV}")

summary = {
    "collision_qids": len(collision_rows),
    "detailed_collision_rows": len(details),

    "confidence_distribution": dict(
        sorted(confidence_counts.items())
    ),

    "dob_check_distribution": dict(
        sorted(dob_counts.items())
    ),

    "entity_type_distribution": dict(
        sorted(entity_type_counts.items())
    ),

    "inherited_distribution": dict(
        sorted(inherited_counts.items())
    ),

    "player_table_coverage": dict(
        sorted(missing_player_counts.items())
    ),

    "largest_collision_group": (
        {
            "qid": collision_rows[0][0],
            "link_rows": collision_rows[0][1],
            "reep_players": collision_rows[0][2],
        }
        if collision_rows
        else None
    ),

    "players_merged": 0,
    "players_deleted": 0,
    "qid_links_modified": 0,
    "source_database_modified": False,
}

print("\nWriting summary JSON...")

with OUTPUT_JSON.open("w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"  JSON written: {OUTPUT_JSON}")

con.close()

print("\n" + "=" * 70)
print("QID COLLISION AUDIT COMPLETE")
print("=" * 70)

print(f"\nCollision QIDs:              {len(collision_rows):,}")
print(f"Detailed collision rows:     {len(details):,}")

if collision_rows:
    print(
        f"Largest collision:          "
        f"{collision_rows[0][0]} "
        f"({collision_rows[0][2]} REEP players)"
    )
else:
    print("Largest collision:           NONE")

print("\nPlayers merged:              0")
print("Players deleted:             0")
print("QID links modified:          0")
print("Source database modified:    NO")

print("\nREEP IDs remain authoritative.")
print("This audit is READ-ONLY.")