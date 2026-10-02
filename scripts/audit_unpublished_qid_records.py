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

OUTPUT_JSON = ROOT / "output" / "reep-unpublished-qid-audit.json"
OUTPUT_CSV = ROOT / "output" / "reep-unpublished-qid-records.csv"

print("=" * 70)
print("REEP UNPUBLISHED QID RECORD AUDIT")
print("=" * 70)

print("\nSource database:")
print(f"  {SOURCE_DB}")

print("\nOpening REEP database READ-ONLY...")

con = duckdb.connect(
    database=str(SOURCE_DB),
    read_only=True
)

print("  Database opened: READ-ONLY")

print("\nFinding QID-linked records absent from main.players...")

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
        e.status,
        e.label,
        e.gender,
        e.country,
        e.corroboration_grade,
        e.corroboration_count,
        e.source_tier_band
    FROM main.overlay_links ol
    LEFT JOIN main.players p
        ON p.reep_id = ol.reep_id
    LEFT JOIN main.entities e
        ON e.reep_id = ol.reep_id
    WHERE p.reep_id IS NULL
    ORDER BY
        ol.entity_type,
        ol.qid,
        ol.reep_id
    """
).fetchall()

print(f"  Unpublished QID-linked rows: {len(rows):,}")

print("\nAnalyzing entity types...")

entity_counts = Counter(
    str(row[4]) for row in rows
)

for key, value in sorted(entity_counts.items()):
    print(f"  {key}: {value:,}")

print("\nAnalyzing entity status...")

status_counts = Counter(
    "NULL" if row[7] is None else str(row[7])
    for row in rows
)

for key, value in sorted(status_counts.items()):
    print(f"  {key}: {value:,}")

print("\nAnalyzing labels...")

label_counts = Counter()

for row in rows:
    label_counts[
        "present" if row[8] not in (None, "") else "NULL"
    ] += 1

for key, value in sorted(label_counts.items()):
    print(f"  {key}: {value:,}")

print("\nAnalyzing entity metadata availability...")

gender_counts = Counter(
    "NULL" if row[9] is None else str(row[9])
    for row in rows
)

country_counts = Counter(
    "NULL" if row[10] is None else str(row[10])
    for row in rows
)

grade_counts = Counter(
    "NULL" if row[11] is None else str(row[11])
    for row in rows
)

tier_counts = Counter(
    "NULL" if row[13] is None else str(row[13])
    for row in rows
)

print("\nGender:")
for key, value in sorted(gender_counts.items()):
    print(f"  {key}: {value:,}")

print("\nCountry:")
for key, value in sorted(country_counts.items()):
    print(f"  {key}: {value:,}")

print("\nCorroboration grade:")
for key, value in sorted(grade_counts.items()):
    print(f"  {key}: {value:,}")

print("\nSource-tier band:")
for key, value in sorted(tier_counts.items()):
    print(f"  {key}: {value:,}")

print("\nChecking redirects...")

redirect_counts = Counter()

for row in rows:
    reep_id = row[1]

    redirect = con.execute(
        """
        SELECT
            reason
        FROM main.redirects
        WHERE from_id = ?
        """,
        [reep_id]
    ).fetchone()

    if redirect is None:
        redirect_counts["no_redirect"] += 1
    else:
        redirect_counts[
            str(redirect[0])
        ] += 1

for key, value in sorted(redirect_counts.items()):
    print(f"  {key}: {value:,}")

print("\nChecking whether records exist in main.entities...")

entity_presence = Counter(
    "entity_present" if row[7] is not None or row[8] is not None
    else "entity_missing"
    for row in rows
)

for key, value in sorted(entity_presence.items()):
    print(f"  {key}: {value:,}")

print("\nSample unpublished QID-linked records:")

for row in rows[:30]:
    (
        qid,
        reep_id,
        confidence,
        dob_check,
        entity_type,
        inherited_count,
        inherited,
        status,
        label,
        gender,
        country,
        corroboration_grade,
        corroboration_count,
        source_tier_band,
    ) = row

    print(
        f"  {reep_id} | "
        f"QID={qid} | "
        f"type={entity_type} | "
        f"label={label} | "
        f"status={status} | "
        f"gender={gender} | "
        f"confidence={confidence} | "
        f"dob={dob_check}"
    )

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
        "confidence",
        "dob_check",
        "entity_type",
        "inherited_count",
        "inherited",
        "entity_status",
        "entity_label",
        "gender",
        "country",
        "corroboration_grade",
        "corroboration_count",
        "source_tier_band",
    ])

    writer.writerows(rows)

print(f"  CSV written: {OUTPUT_CSV}")

summary = {
    "unpublished_qid_link_rows": len(rows),
    "entity_type_distribution": dict(
        sorted(entity_counts.items())
    ),
    "status_distribution": dict(
        sorted(status_counts.items())
    ),
    "label_distribution": dict(
        sorted(label_counts.items())
    ),
    "gender_distribution": dict(
        sorted(gender_counts.items())
    ),
    "country_distribution": dict(
        sorted(country_counts.items())
    ),
    "corroboration_grade_distribution": dict(
        sorted(grade_counts.items())
    ),
    "source_tier_band_distribution": dict(
        sorted(tier_counts.items())
    ),
    "redirect_distribution": dict(
        sorted(redirect_counts.items())
    ),
    "entity_presence": dict(
        sorted(entity_presence.items())
    ),
    "records_modified": 0,
    "source_database_modified": False,
}

print("\nWriting JSON summary...")

with OUTPUT_JSON.open("w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"  JSON written: {OUTPUT_JSON}")

con.close()

print("\n" + "=" * 70)
print("UNPUBLISHED QID AUDIT COMPLETE")
print("=" * 70)

print(f"\nUnpublished QID-linked rows: {len(rows):,}")

print("\nRecords modified:            0")
print("Source database modified:    NO")
print("Database access:             READ-ONLY")

print("\nREEP IDs remain authoritative.")