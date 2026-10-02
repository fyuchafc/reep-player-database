"""
Build the REEP master player dataset.

SOURCE:
    output/players.json

This script:
- Reads the validated REEP player extraction.
- Creates a master JSON and CSV.
- Preserves REEP identity exactly.
- Does not modify the source DuckDB.
- Does not perform FYUCHA matching.
- Does not invent DOB, nationality, or career information.
"""

from pathlib import Path
import csv
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"

INPUT_JSON = OUTPUT_DIR / "players.json"
MASTER_JSON = OUTPUT_DIR / "reep-player-master.json"
MASTER_CSV = OUTPUT_DIR / "reep-player-master.csv"


REQUIRED_FIELDS = [
    "reep_id",
    "status",
    "label",
    "gender",
    "country",
    "corroboration_grade",
    "corroboration_count",
    "source_tier_band",
]


def fail(message):
    print()
    print("ERROR:")
    print(f"  {message}")
    sys.exit(1)


def load_players():
    print("=" * 70)
    print("BUILDING REEP PLAYER MASTER")
    print("=" * 70)
    print()

    print("Project root:")
    print(f"  {PROJECT_ROOT}")
    print()

    print("Input:")
    print(f"  {INPUT_JSON}")
    print()

    if not INPUT_JSON.exists():
        fail("players.json does not exist. Run extract_players.py first.")

    print("Loading extracted players...")

    try:
        with INPUT_JSON.open("r", encoding="utf-8") as f:
            players = json.load(f)
    except Exception as exc:
        fail(f"Could not read players.json: {exc}")

    if not isinstance(players, list):
        fail("players.json must contain a JSON list.")

    print(f"  Records loaded: {len(players):,}")
    print()

    return players


def validate_players(players):
    print("Validating master input...")

    if not players:
        fail("No player records were loaded.")

    seen = set()
    duplicate_ids = 0
    empty_ids = 0
    empty_labels = 0
    missing_fields = 0

    for player in players:
        if not isinstance(player, dict):
            fail("A player record is not a JSON object.")

        for field in REQUIRED_FIELDS:
            if field not in player:
                missing_fields += 1

        reep_id = player.get("reep_id")
        label = player.get("label")

        if reep_id is None or str(reep_id).strip() == "":
            empty_ids += 1
        else:
            if reep_id in seen:
                duplicate_ids += 1
            seen.add(reep_id)

        if label is None or str(label).strip() == "":
            empty_labels += 1

    print(f"  Unique REEP IDs:    {len(seen):,}")
    print(f"  Duplicate IDs:      {duplicate_ids:,}")
    print(f"  Empty REEP IDs:      {empty_ids:,}")
    print(f"  Empty labels:        {empty_labels:,}")
    print(f"  Missing fields:      {missing_fields:,}")

    if duplicate_ids:
        fail("Duplicate REEP IDs detected.")

    if empty_ids:
        fail("Empty REEP IDs detected.")

    if empty_labels:
        fail("Empty player labels detected.")

    if missing_fields:
        fail("Required fields are missing.")

    print("  Validation:          OK")
    print()


def build_master(players):
    print("Building master records...")

    master = []

    for player in players:
        record = {
            "reep_id": player.get("reep_id"),
            "status": player.get("status"),
            "label": player.get("label"),
            "gender": player.get("gender"),
            "country": player.get("country"),
            "corroboration_grade": player.get("corroboration_grade"),
            "corroboration_count": player.get("corroboration_count"),
            "source_tier_band": player.get("source_tier_band"),
        }

        master.append(record)

    master.sort(key=lambda x: x["reep_id"])

    print(f"  Master records:     {len(master):,}")
    print()

    return master


def validate_master(master, original_count):
    print("Validating built master...")

    if len(master) != original_count:
        fail(
            f"Record count changed: input={original_count:,}, "
            f"master={len(master):,}"
        )

    ids = [record["reep_id"] for record in master]

    if len(ids) != len(set(ids)):
        fail("Duplicate REEP IDs detected in built master.")

    if ids != sorted(ids):
        fail("Master records are not sorted by REEP ID.")

    print(f"  Records checked:    {len(master):,}")
    print(f"  Unique REEP IDs:     {len(set(ids)):,}")
    print("  Record count:        OK")
    print("  Identity uniqueness: OK")
    print("  Ordering:            OK")
    print()


def write_json(master):
    print("Writing master JSON...")
    with MASTER_JSON.open("w", encoding="utf-8") as f:
        json.dump(
            master,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"  JSON written:        {MASTER_JSON}")
    print()


def write_csv(master):
    print("Writing master CSV...")

    with MASTER_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=REQUIRED_FIELDS,
        )

        writer.writeheader()
        writer.writerows(master)

    print(f"  CSV written:         {MASTER_CSV}")
    print()


def print_summary(master):
    status_counts = {}

    for record in master:
        status = record.get("status")
        status_counts[status] = status_counts.get(status, 0) + 1

    gender_counts = {}

    for record in master:
        gender = record.get("gender")
        gender_key = "NULL" if gender is None else gender
        gender_counts[gender_key] = gender_counts.get(gender_key, 0) + 1

    print("=" * 70)
    print("MASTER BUILD COMPLETE")
    print("=" * 70)
    print()

    print(f"REEP players:          {len(master):,}")
    print()

    print("Status distribution:")
    for status, count in sorted(
        status_counts.items(),
        key=lambda x: str(x[0]),
    ):
        print(f"  {str(status):18} {count:>10,}")

    print()

    print("Gender distribution:")
    for gender, count in sorted(
        gender_counts.items(),
        key=lambda x: str(x[0]),
    ):
        print(f"  {str(gender):18} {count:>10,}")

    print()

    print("Master files:")
    print(f"  {MASTER_JSON}")
    print(f"  {MASTER_CSV}")
    print()

    print("Source players.json was not modified.")
    print("Original REEP DuckDB was not accessed.")
    print("No FYUCHA matching was performed.")
    print("No DOBs or nationality values were invented.")
    print()


def main():
    players = load_players()

    validate_players(players)

    master = build_master(players)

    validate_master(
        master,
        len(players),
    )

    write_json(master)
    write_csv(master)

    print_summary(master)


if __name__ == "__main__":
    main()