"""
Normalize REEP player names for search and analysis.

IMPORTANT:
- The original REEP label is preserved unchanged.
- No identity matching is performed.
- No records are merged.
- No DOB, nationality, or career information is invented.
- REEP IDs remain the authoritative identity.
"""

from pathlib import Path
import csv
import json
import re
import sys
import unicodedata


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "output"

INPUT_JSON = OUTPUT_DIR / "reep-player-master.json"
OUTPUT_JSON = OUTPUT_DIR / "reep-player-normalized.json"
OUTPUT_CSV = OUTPUT_DIR / "reep-player-normalized.csv"


OUTPUT_FIELDS = [
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


def normalize_name(value):
    """
    Create a conservative normalized form.

    Steps:
    1. Unicode normalization.
    2. Remove diacritics.
    3. Convert to lowercase.
    4. Replace punctuation with spaces.
    5. Collapse repeated whitespace.

    The original label is never changed.
    """

    if value is None:
        return ""

    text = str(value).strip()

    decomposed = unicodedata.normalize("NFKD", text)

    without_marks = "".join(
        char
        for char in decomposed
        if not unicodedata.combining(char)
    )

    lowered = without_marks.lower()

    cleaned = re.sub(
        r"[^\w\s]",
        " ",
        lowered,
        flags=re.UNICODE,
    )

    collapsed = re.sub(
        r"\s+",
        " ",
        cleaned,
    ).strip()

    return collapsed


def build_search_name(normalized_name):
    """
    Search representation.

    This currently mirrors the conservative normalized name.
    Keeping it as a separate field allows future search improvements
    without changing normalized_name.
    """

    return normalized_name


def load_master():
    print("=" * 70)
    print("REEP PLAYER NORMALIZATION")
    print("=" * 70)
    print()

    print("Project root:")
    print(f"  {PROJECT_ROOT}")
    print()

    print("Input master:")
    print(f"  {INPUT_JSON}")
    print()

    if not INPUT_JSON.exists():
        fail(
            "reep-player-master.json does not exist. "
            "Run build_master.py first."
        )

    print("Loading REEP master...")

    try:
        with INPUT_JSON.open("r", encoding="utf-8") as f:
            players = json.load(f)
    except Exception as exc:
        fail(f"Could not read master JSON: {exc}")

    if not isinstance(players, list):
        fail("Master JSON must contain a JSON list.")

    print(f"  Records loaded: {len(players):,}")
    print()

    return players


def validate_input(players):
    print("Validating input master...")

    required = [
        "reep_id",
        "status",
        "label",
        "gender",
        "country",
        "corroboration_grade",
        "corroboration_count",
        "source_tier_band",
    ]

    seen = set()

    for index, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            fail(f"Record {index} is not a JSON object.")

        for field in required:
            if field not in player:
                fail(
                    f"Record {index} is missing required field: "
                    f"{field}"
                )

        reep_id = player["reep_id"]
        label = player["label"]

        if reep_id is None or str(reep_id).strip() == "":
            fail(f"Record {index} has an empty REEP ID.")

        if reep_id in seen:
            fail(f"Duplicate REEP ID detected: {reep_id}")

        seen.add(reep_id)

        if label is None or str(label).strip() == "":
            fail(f"Record {index} has an empty label.")

    print(f"  Records checked: {len(players):,}")
    print(f"  Unique REEP IDs: {len(seen):,}")
    print("  Validation:      OK")
    print()


def normalize_players(players):
    print("Creating normalized fields...")

    normalized = []

    for player in players:
        original_label = player["label"]

        normalized_name = normalize_name(
            original_label
        )

        search_name = build_search_name(
            normalized_name
        )

        record = {
            "reep_id": player["reep_id"],
            "status": player["status"],
            "label": original_label,
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
            "normalized_name": normalized_name,
            "search_name": search_name,
        }

        normalized.append(record)

    print(f"  Records normalized: {len(normalized):,}")
    print()

    return normalized


def validate_normalized(original, normalized):
    print("Validating normalized output...")

    if len(original) != len(normalized):
        fail(
            f"Record count changed: "
            f"{len(original):,} -> {len(normalized):,}"
        )

    original_ids = [p["reep_id"] for p in original]
    normalized_ids = [p["reep_id"] for p in normalized]

    if original_ids != normalized_ids:
        fail(
            "REEP ID ordering or membership changed."
        )

    for source, result in zip(original, normalized):
        if source["label"] != result["label"]:
            fail(
                f"Original label changed for "
                f"{source['reep_id']}"
            )

        if not result["normalized_name"]:
            fail(
                f"Empty normalized name for "
                f"{source['reep_id']}"
            )

        if result["search_name"] != result["normalized_name"]:
            fail(
                f"Unexpected search-name difference for "
                f"{source['reep_id']}"
            )

    print(f"  Records checked:    {len(normalized):,}")
    print("  Record count:       OK")
    print("  REEP IDs:           OK")
    print("  Original labels:    PRESERVED")
    print("  Normalized names:   OK")
    print("  Search names:       OK")
    print()


def write_json(players):
    print("Writing normalized JSON...")

    with OUTPUT_JSON.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            players,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"  JSON written: {OUTPUT_JSON}")
    print()


def write_csv(players):
    print("Writing normalized CSV...")

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=OUTPUT_FIELDS,
        )

        writer.writeheader()
        writer.writerows(players)

    print(f"  CSV written: {OUTPUT_CSV}")
    print()


def print_samples(players):
    print("Normalization samples:")

    for player in players[:10]:
        print()
        print(f"  REEP ID:          {player['reep_id']}")
        print(f"  Original label:   {player['label']}")
        print(f"  Normalized name:  {player['normalized_name']}")
        print(f"  Search name:      {player['search_name']}")

    print()

    print("=" * 70)
    print("NORMALIZATION COMPLETE")
    print("=" * 70)
    print()

    print(f"REEP players: {len(players):,}")
    print()

    print("Output files:")
    print(f"  {OUTPUT_JSON}")
    print(f"  {OUTPUT_CSV}")
    print()

    print("Original REEP labels were preserved.")
    print("No players were merged.")
    print("No identity matching was performed.")
    print("No source database was modified.")
    print()


def main():
    players = load_master()

    validate_input(players)

    normalized = normalize_players(players)

    validate_normalized(
        players,
        normalized,
    )

    write_json(normalized)
    write_csv(normalized)

    print_samples(normalized)


if __name__ == "__main__":
    main()