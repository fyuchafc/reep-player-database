"""
REEP-only duplicate analysis.

IMPORTANT:
- This script does NOT merge players.
- This script does NOT delete players.
- REEP IDs remain authoritative.
- Analysis is based only on the REEP normalized player dataset.
- Cross-database matching is NOT performed.

The purpose is to identify:
1. Exact normalized-name collisions.
2. How many REEP records are involved.
3. Which normalized names occur more than once.
"""

from pathlib import Path
from collections import defaultdict
import csv
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"

INPUT_JSON = OUTPUT_DIR / "reep-player-normalized.json"

COLLISION_JSON = OUTPUT_DIR / "reep-name-collisions.json"
COLLISION_CSV = OUTPUT_DIR / "reep-name-collisions.csv"
SUMMARY_JSON = OUTPUT_DIR / "reep-duplicate-analysis.json"


REQUIRED_FIELDS = [
    "reep_id",
    "status",
    "label",
    "gender",
    "country",
    "corroboration_grade",
    "corroboration_count",
    "source_tier_band",
    "normalized_name",
    "search_name",
]


def fail(message):
    print()
    print("ERROR:")
    print(f"  {message}")
    sys.exit(1)


def load_players():
    print("=" * 70)
    print("REEP DUPLICATE ANALYSIS")
    print("=" * 70)
    print()

    print("Project root:")
    print(f"  {PROJECT_ROOT}")
    print()

    print("Input:")
    print(f"  {INPUT_JSON}")
    print()

    if not INPUT_JSON.exists():
        fail(
            "reep-player-normalized.json does not exist. "
            "Run normalize_players.py first."
        )

    print("Loading normalized REEP players...")

    try:
        with INPUT_JSON.open("r", encoding="utf-8") as f:
            players = json.load(f)
    except Exception as exc:
        fail(f"Could not read normalized player file: {exc}")

    if not isinstance(players, list):
        fail("Normalized player file must contain a JSON list.")

    print(f"  Records loaded: {len(players):,}")
    print()

    return players


def validate_players(players):
    print("Validating normalized input...")

    seen_ids = set()

    for index, player in enumerate(players, start=1):

        if not isinstance(player, dict):
            fail(f"Record {index} is not a JSON object.")

        for field in REQUIRED_FIELDS:
            if field not in player:
                fail(
                    f"Record {index} is missing field: {field}"
                )

        reep_id = player["reep_id"]

        if reep_id is None or str(reep_id).strip() == "":
            fail(
                f"Record {index} has an empty REEP ID."
            )

        if reep_id in seen_ids:
            fail(
                f"Duplicate REEP ID detected: {reep_id}"
            )

        seen_ids.add(reep_id)

        if not player["normalized_name"]:
            fail(
                f"Record {index} has an empty normalized name."
            )

    print(f"  Records checked: {len(players):,}")
    print(f"  Unique REEP IDs: {len(seen_ids):,}")
    print("  Validation:      OK")
    print()


def build_name_groups(players):
    print("Grouping players by normalized name...")

    groups = defaultdict(list)

    for player in players:
        name = player["normalized_name"]

        groups[name].append(
            {
                "reep_id": player["reep_id"],
                "label": player["label"],
                "status": player["status"],
                "gender": player["gender"],
                "country": player["country"],
                "corroboration_grade": player[
                    "corroboration_grade"
                ],
                "corroboration_count": player[
                    "corroboration_count"
                ],
                "source_tier_band": player[
                    "source_tier_band"
                ],
            }
        )

    print(f"  Distinct normalized names: {len(groups):,}")
    print()

    return groups


def extract_collisions(groups):
    print("Identifying exact normalized-name collisions...")

    collisions = []

    for normalized_name, records in groups.items():

        if len(records) <= 1:
            continue

        records_sorted = sorted(
            records,
            key=lambda x: x["reep_id"],
        )

        collisions.append(
            {
                "normalized_name": normalized_name,
                "record_count": len(records_sorted),
                "reep_ids": [
                    record["reep_id"]
                    for record in records_sorted
                ],
                "records": records_sorted,
            }
        )

    collisions.sort(
        key=lambda x: (
            -x["record_count"],
            x["normalized_name"],
        )
    )

    return collisions


def calculate_summary(players, groups, collisions):
    collision_player_count = sum(
        item["record_count"]
        for item in collisions
    )

    collision_name_count = len(collisions)

    unique_name_count = sum(
        1
        for records in groups.values()
        if len(records) == 1
    )

    largest_collision = 0

    if collisions:
        largest_collision = max(
            item["record_count"]
            for item in collisions
        )

    return {
        "total_players": len(players),
        "distinct_normalized_names": len(groups),
        "unique_normalized_names": unique_name_count,
        "collision_name_groups": collision_name_count,
        "players_in_collision_groups": collision_player_count,
        "players_with_unique_normalized_name": unique_name_count,
        "largest_collision_group": largest_collision,
        "cross_database_matching_performed": False,
        "players_merged": 0,
        "players_deleted": 0,
    }


def write_collision_json(collisions):
    print("Writing collision JSON...")

    with COLLISION_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            collisions,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"  JSON written: {COLLISION_JSON}")
    print()


def write_collision_csv(collisions):
    print("Writing collision CSV...")

    with COLLISION_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        fieldnames = [
            "normalized_name",
            "record_count",
            "reep_ids",
            "labels",
            "statuses",
            "genders",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for collision in collisions:

            records = collision["records"]

            writer.writerow(
                {
                    "normalized_name":
                        collision["normalized_name"],

                    "record_count":
                        collision["record_count"],

                    "reep_ids":
                        " | ".join(
                            record["reep_id"]
                            for record in records
                        ),

                    "labels":
                        " | ".join(
                            str(record["label"])
                            for record in records
                        ),

                    "statuses":
                        " | ".join(
                            str(record["status"])
                            for record in records
                        ),

                    "genders":
                        " | ".join(
                            "NULL"
                            if record["gender"] is None
                            else str(record["gender"])
                            for record in records
                        ),
                }
            )

    print(f"  CSV written: {COLLISION_CSV}")
    print()


def write_summary(summary):
    print("Writing analysis summary...")

    with SUMMARY_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"  Summary written: {SUMMARY_JSON}")
    print()


def print_summary(summary, collisions):
    print("=" * 70)
    print("DUPLICATE ANALYSIS COMPLETE")
    print("=" * 70)
    print()

    print(
        f"Total REEP players:              "
        f"{summary['total_players']:,}"
    )

    print(
        f"Distinct normalized names:       "
        f"{summary['distinct_normalized_names']:,}"
    )

    print(
        f"Unique normalized names:         "
        f"{summary['unique_normalized_names']:,}"
    )

    print(
        f"Collision name groups:           "
        f"{summary['collision_name_groups']:,}"
    )

    print(
        f"Players in collision groups:     "
        f"{summary['players_in_collision_groups']:,}"
    )

    print(
        f"Largest collision group:         "
        f"{summary['largest_collision_group']:,}"
    )

    print()

    print("Players merged:                  0")
    print("Players deleted:                0")
    print("Cross-database matching:        NO")
    print()

    print("Output files:")
    print(f"  {COLLISION_JSON}")
    print(f"  {COLLISION_CSV}")
    print(f"  {SUMMARY_JSON}")
    print()

    print("Top collision groups:")

    for collision in collisions[:20]:

        print()
        print(
            f"  {collision['normalized_name']}"
            f"  ({collision['record_count']} records)"
        )

        for record in collision["records"]:
            gender = (
                "NULL"
                if record["gender"] is None
                else record["gender"]
            )

            print(
                f"    {record['reep_id']} | "
                f"{record['label']} | "
                f"{record['status']} | "
                f"{gender}"
            )

    print()

    print("No identities were merged.")
    print("No identities were deleted.")
    print("REEP IDs remain authoritative.")
    print("Original normalized input was not modified.")
    print()


def main():
    players = load_players()

    validate_players(players)

    groups = build_name_groups(players)

    collisions = extract_collisions(groups)

    summary = calculate_summary(
        players,
        groups,
        collisions,
    )

    write_collision_json(collisions)
    write_collision_csv(collisions)
    write_summary(summary)

    print_summary(
        summary,
        collisions,
    )


if __name__ == "__main__":
    main()