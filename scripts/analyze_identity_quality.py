from pathlib import Path
import json
import csv
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "output" / "reep-player-master.json"
OUTPUT_JSON = ROOT / "output" / "reep-identity-quality.json"
OUTPUT_CSV = ROOT / "output" / "reep-identity-quality.csv"

print("=" * 70)
print("REEP IDENTITY QUALITY ANALYSIS")
print("=" * 70)

print("\nLoading REEP master players...")
with INPUT.open("r", encoding="utf-8") as f:
    players = json.load(f)

print(f"  Records loaded: {len(players):,}")

print("\nValidating input...")

required = {
    "reep_id",
    "status",
    "label",
    "gender",
    "country",
    "corroboration_grade",
    "corroboration_count",
    "source_tier_band",
}

for i, player in enumerate(players, 1):
    missing = required - set(player.keys())
    if missing:
        raise ValueError(
            f"Record {i} is missing fields: {sorted(missing)}"
        )

reep_ids = [p["reep_id"] for p in players]

if len(reep_ids) != len(set(reep_ids)):
    raise ValueError("Duplicate REEP IDs detected.")

print(f"  Records checked: {len(players):,}")
print(f"  Unique REEP IDs: {len(set(reep_ids)):,}")
print("  Validation:      OK")

print("\nAnalyzing identity-quality fields...")

grade_counts = Counter(
    p["corroboration_grade"] for p in players
)

count_counts = Counter(
    p["corroboration_count"] for p in players
)

band_counts = Counter(
    p["source_tier_band"] for p in players
)

status_counts = Counter(
    p["status"] for p in players
)

gender_counts = Counter(
    "NULL" if p["gender"] is None else p["gender"]
    for p in players
)

country_present = sum(
    1 for p in players
    if p["country"] not in (None, "")
)

label_present = sum(
    1 for p in players
    if p["label"] not in (None, "")
)

print("\nCorroboration grade:")
for key, value in sorted(grade_counts.items(), key=lambda x: str(x[0])):
    print(f"  {key}: {value:,}")

print("\nCorroboration count:")
for key, value in sorted(count_counts.items(), key=lambda x: str(x[0])):
    print(f"  {key}: {value:,}")

print("\nSource-tier band:")
for key, value in sorted(band_counts.items(), key=lambda x: str(x[0])):
    print(f"  {key}: {value:,}")

print("\nStatus:")
for key, value in sorted(status_counts.items()):
    print(f"  {key}: {value:,}")

print("\nGender:")
for key, value in sorted(gender_counts.items()):
    print(f"  {key}: {value:,}")

print("\nField completeness:")
print(f"  Labels present:   {label_present:,}")
print(f"  Labels missing:   {len(players) - label_present:,}")
print(f"  Country present:  {country_present:,}")
print(f"  Country missing:  {len(players) - country_present:,}")

summary = {
    "total_players": len(players),
    "unique_reep_ids": len(set(reep_ids)),
    "corroboration_grade_distribution": dict(
        sorted(grade_counts.items(), key=lambda x: str(x[0]))
    ),
    "corroboration_count_distribution": dict(
        sorted(count_counts.items(), key=lambda x: str(x[0]))
    ),
    "source_tier_band_distribution": dict(
        sorted(band_counts.items(), key=lambda x: str(x[0]))
    ),
    "status_distribution": dict(sorted(status_counts.items())),
    "gender_distribution": dict(sorted(gender_counts.items())),
    "label_present": label_present,
    "label_missing": len(players) - label_present,
    "country_present": country_present,
    "country_missing": len(players) - country_present,
    "players_merged": 0,
    "players_deleted": 0,
    "cross_database_matching_performed": False,
}

print("\nWriting identity-quality JSON...")
with OUTPUT_JSON.open("w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(f"  JSON written: {OUTPUT_JSON}")

print("\nWriting identity-quality CSV...")

rows = []

for player in players:
    rows.append({
        "reep_id": player["reep_id"],
        "label": player["label"],
        "status": player["status"],
        "gender": player["gender"],
        "country": player["country"],
        "corroboration_grade": player["corroboration_grade"],
        "corroboration_count": player["corroboration_count"],
        "source_tier_band": player["source_tier_band"],
    })

with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "reep_id",
            "label",
            "status",
            "gender",
            "country",
            "corroboration_grade",
            "corroboration_count",
            "source_tier_band",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

print(f"  CSV written: {OUTPUT_CSV}")

print("\n" + "=" * 70)
print("IDENTITY QUALITY ANALYSIS COMPLETE")
print("=" * 70)

print(f"\nTotal REEP players:       {len(players):,}")
print(f"Unique REEP IDs:          {len(set(reep_ids)):,}")
print(f"Labels present:           {label_present:,}")
print(f"Country present:          {country_present:,}")

print("\nPlayers merged:           0")
print("Players deleted:          0")
print("Cross-database matching:  NO")

print("\nOutput files:")
print(f"  {OUTPUT_JSON}")
print(f"  {OUTPUT_CSV}")

print("\nREEP IDs remain authoritative.")
print("Original master input was not modified.")