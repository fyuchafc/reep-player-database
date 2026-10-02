from pathlib import Path
import json
import csv
import duckdb
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DB = (
    ROOT.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

OUTPUT_JSON = ROOT / "output" / "reep-player-qid-collision-audit.json"
OUTPUT_CSV = ROOT / "output" / "reep-player-qid-collisions.csv"

print("=" * 70)
print("REEP PLAYER QID COLLISION AUDIT")
print("=" * 70)

print("\nSource database:")
print(f"  {SOURCE_DB}")

print("\nOpening REEP database READ-ONLY...")

con = duckdb.connect(
    database=str(SOURCE_DB),
    read_only=True
)

print("  Database opened: READ-ONLY")

print("\nExtracting QID links for actual REEP players...")

rows = con.execute(
    """
    SELECT
        ol.qid,
        ol.reep_id,
        ol.confidence,
        ol.dob_check,
        ol.entity_type,
        ol.inherited_count,
        ol.inherited,
        p.status,
        p.label,
        p.gender
    FROM main.overlay_links ol
    INNER JOIN main.players p
        ON p.reep_id = ol.reep_id
    WHERE ol.qid IS NOT NULL
      AND TRIM(ol.qid) <> ''
    ORDER BY
        ol.qid,
        ol.reep_id
    """
).fetchall()

print(f"  Player QID-link rows: {len(rows):,}")

print("\nChecking player QID identity consistency...")

qid_players = defaultdict(list)

for row in rows:
    qid_players[row[0]].append(row)

collision_groups = {
    qid: records
    for qid, records in qid_players.items()
    if len({r[1] for r in records}) > 1
}

collision_rows = sum(
    len(records)
    for records in collision_groups.values()
)

print(f"  Distinct player QIDs: {len(qid_players):,}")
print(f"  Player QID collision groups: {len(collision_groups):,}")
print(f"  Rows belonging to collision groups: {collision_rows:,}")

print("\nAnalyzing collision sizes...")

collision_size_counts = Counter(
    len({r[1] for r in records})
    for records in collision_groups.values()
)

for size, count in sorted(collision_size_counts.items()):
    print(f"  {size} players sharing QID: {count:,} QIDs")

print("\nAnalyzing collision confidence...")

confidence_counts = Counter()

for records in collision_groups.values():
    for row in records:
        confidence_counts[
            str(row[2]) if row[2] is not None else "NULL"
        ] += 1

for key, value in sorted(confidence_counts.items()):
    print(f"  {key}: {value:,}")

print("\nAnalyzing DOB verification...")

dob_counts = Counter()

for records in collision_groups.values():
    for row in records:
        dob_counts[
            str(row[3]) if row[3] is not None else "NULL"
        ] += 1

for key, value in sorted(dob_counts.items()):
    print(f"  {key}: {value:,}")

print("\nAnalyzing player status...")

status_counts = Counter()

for records in collision_groups.values():
    for row in records:
        status_counts[
            str(row[7]) if row[7] is not None else "NULL"
        ] += 1

for key, value in sorted(status_counts.items()):
    print(f"  {key}: {value:,}")

print("\nAnalyzing labels...")

label_counts = Counter()

for records in collision_groups.values():
    for row in records:
        label_counts[
            "present" if row[8] not in (None, "") else "NULL"
        ] += 1

for key, value in sorted(label_counts.items()):
    print(f"  {key}: {value:,}")

print("\nAnalyzing gender...")

gender_counts = Counter()

for records in collision_groups.values():
    for row in records:
        gender_counts[
            str(row[9]) if row[9] is not None else "NULL"
        ] += 1

for key, value in sorted(gender_counts.items()):
    print(f"  {key}: {value:,}")

print("\nChecking whether collision records are inherited...")

inherited_counts = Counter()

for records in collision_groups.values():
    for row in records:
        inherited_counts[
            str(row[6]) if row[6] is not None else "NULL"
        ] += 1

for key, value in sorted(inherited_counts.items()):
    print(f"  {key}: {value:,}")

print("\nGenerating detailed collision records...")

detailed_rows = []

for qid in sorted(collision_groups):
    records = collision_groups[qid]

    unique_players = {}

    for row in records:
        unique_players[row[1]] = row

    player_list = list(unique_players.values())

    for row in player_list:
        (
            qid_value,
            reep_id,
            confidence,
            dob_check,
            entity_type,
            inherited_count,
            inherited,
            status,
            label,
            gender,
        ) = row

        other_players = [
            r[1]
            for r in player_list
            if r[1] != reep_id
        ]

        other_labels = [
            r[8]
            for r in player_list
            if r[1] != reep_id
        ]

        detailed_rows.append([
            qid_value,
            reep_id,
            len(player_list),
            confidence,
            dob_check,
            entity_type,
            inherited_count,
            inherited,
            status,
            label,
            gender,
            "; ".join(other_players),
            "; ".join(
                str(x) for x in other_labels
                if x not in (None, "")
            ),
        ])

print(f"  Detailed collision rows: {len(detailed_rows):,}")

print("\nShowing largest player-only collisions...")

largest = sorted(
    collision_groups.items(),
    key=lambda item: (
        -len({r[1] for r in item[1]}),
        item[0]
    )
)[:30]

for qid, records in largest:
    players = {}

    for row in records:
        players[row[1]] = row

    print(
        f"\n  QID {qid} → {len(players)} REEP players"
    )

    for row in players.values():
        print(
            f"    {row[1]} | "
            f"{row[8]} | "
            f"status={row[7]} | "
            f"gender={row[9]} | "
            f"confidence={row[2]} | "
            f"dob={row[3]}"
        )

print("\nChecking whether collision players have different labels...")

same_label_groups = 0
different_label_groups = 0

for qid, records in collision_groups.items():

    labels = {
        str(row[8]).strip().casefold()
        for row in records
        if row[8] not in (None, "")
    }

    if len(labels) <= 1:
        same_label_groups += 1
    else:
        different_label_groups += 1

print(f"  Same-label collision groups: {same_label_groups:,}")
print(f"  Different-label collision groups: {different_label_groups:,}")

print("\nChecking entity_type values inside player table...")

entity_type_counts = Counter(
    str(row[4]) if row[4] is not None else "NULL"
    for row in rows
)

for key, value in sorted(entity_type_counts.items()):
    print(f"  {key}: {value:,}")

print("\nWriting CSV...")

with OUTPUT_CSV.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "qid",
        "reep_id",
        "players_sharing_qid",
        "confidence",
        "dob_check",
        "entity_type",
        "inherited_count",
        "inherited",
        "status",
        "label",
        "gender",
        "other_reep_ids",
        "other_labels",
    ])

    writer.writerows(detailed_rows)

print(f"  CSV written: {OUTPUT_CSV}")

summary = {
    "player_qid_link_rows": len(rows),
    "distinct_player_qids": len(qid_players),
    "player_qid_collision_groups": len(collision_groups),
    "collision_rows": collision_rows,
    "collision_size_distribution": {
        str(k): v
        for k, v in sorted(collision_size_counts.items())
    },
    "collision_confidence_distribution": dict(
        sorted(confidence_counts.items())
    ),
    "collision_dob_distribution": dict(
        sorted(dob_counts.items())
    ),
    "collision_status_distribution": dict(
        sorted(status_counts.items())
    ),
    "collision_label_distribution": dict(
        sorted(label_counts.items())
    ),
    "collision_gender_distribution": dict(
        sorted(gender_counts.items())
    ),
    "collision_inherited_distribution": dict(
        sorted(inherited_counts.items())
    ),
    "entity_type_distribution": dict(
        sorted(entity_type_counts.items())
    ),
    "same_label_collision_groups": same_label_groups,
    "different_label_collision_groups": different_label_groups,
    "records_modified": 0,
    "source_database_modified": False,
}

print("\nWriting JSON summary...")

with OUTPUT_JSON.open("w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"  JSON written: {OUTPUT_JSON}")

con.close()

print("\n" + "=" * 70)
print("PLAYER QID COLLISION AUDIT COMPLETE")
print("=" * 70)

print(f"\nPlayer QID links:             {len(rows):,}")
print(f"Distinct player QIDs:        {len(qid_players):,}")
print(f"Player collision groups:     {len(collision_groups):,}")
print(f"Collision rows:              {collision_rows:,}")

print("\nRecords modified:             0")
print("Source database modified:     NO")
print("Database access:              READ-ONLY")

print("\nREEP IDs remain authoritative.")