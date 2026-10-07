import csv
import json
import os
from collections import Counter


# ============================================================
# REEP — WIKIDATA MULTIPLE DOB CLAIM AUDIT
# ============================================================
#
# READ-ONLY.
#
# Source:
#   output\reep-wikidata-dob-graphql-audit.json
#
# Purpose:
#   Analyse every player whose Wikidata entity has more than
#   one P569 (date of birth) claim.
#
# This script DOES NOT:
#   - modify the REEP database
#   - modify v1.0.0
#   - choose a canonical DOB
#   - discard any DOB claim
#
# It only classifies the evidence.
# ============================================================


INPUT_FILE = os.path.join(
    "output",
    "reep-wikidata-dob-graphql-audit.json"
)

OUTPUT_CSV = os.path.join(
    "output",
    "reep-wikidata-multiple-dob-claims.csv"
)

OUTPUT_JSON = os.path.join(
    "output",
    "reep-wikidata-multiple-dob-claims.json"
)


# ============================================================
# HELPERS
# ============================================================

def precision_name(value):
    if value == 11:
        return "day"
    if value == 10:
        return "month"
    if value == 9:
        return "year"
    return "other"


def split_dates(value):
    if not value:
        return []

    return [
        x.strip()
        for x in str(value).split(";")
        if x.strip()
    ]


def classify_claim_pattern(
    preferred_count,
    normal_count,
    deprecated_count,
    dates,
    precisions
):

    unique_dates = sorted(set(dates))
    unique_precisions = sorted(set(precisions))

    # --------------------------------------------------------
    # No usable DOB claims
    # --------------------------------------------------------

    if not dates:
        return "no_usable_dob"

    # --------------------------------------------------------
    # All claims point to the same DOB
    # --------------------------------------------------------

    if len(unique_dates) == 1:

        if preferred_count > 0:
            return "same_dob_preferred"

        if normal_count > 0:
            return "same_dob_normal"

        return "same_dob_deprecated_only"

    # --------------------------------------------------------
    # Multiple dates — preferred evidence exists
    # --------------------------------------------------------

    if preferred_count > 0:

        if normal_count > 0:
            return "multiple_dates_preferred_and_normal"

        if deprecated_count > 0:
            return "multiple_dates_preferred_and_deprecated"

        return "multiple_dates_preferred_only"

    # --------------------------------------------------------
    # Multiple dates — no preferred claim
    # --------------------------------------------------------

    if normal_count > 0:

        if deprecated_count > 0:
            return "multiple_dates_normal_and_deprecated"

        return "multiple_dates_normal_only"

    # --------------------------------------------------------
    # Only deprecated claims
    # --------------------------------------------------------

    return "multiple_dates_deprecated_only"


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("WIKIDATA MULTIPLE DOB CLAIM AUDIT")
    print("=" * 70)
    print()

    if not os.path.exists(INPUT_FILE):
        print("ERROR:")
        print(f"Input file not found: {INPUT_FILE}")
        return

    print(
        f"Reading: {INPUT_FILE}"
    )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    print(
        f"Total GraphQL result rows: {len(data):,}"
    )

    print()

    multiple = []

    total_claims = 0

    # --------------------------------------------------------
    # Analyse rows
    # --------------------------------------------------------

    for row in data:

        claim_count = int(
            row.get(
                "dob_claim_count",
                0
            )
            or 0
        )

        if claim_count <= 1:
            continue

        dates = split_dates(
            row.get(
                "dob_values",
                ""
            )
        )

        preferred_count = int(
            row.get(
                "preferred_claim_count",
                0
            )
            or 0
        )

        normal_count = int(
            row.get(
                "normal_claim_count",
                0
            )
            or 0
        )

        deprecated_count = int(
            row.get(
                "deprecated_claim_count",
                0
            )
            or 0
        )

        day_count = int(
            row.get(
                "day_precision_count",
                0
            )
            or 0
        )

        month_count = int(
            row.get(
                "month_precision_count",
                0
            )
            or 0
        )

        year_count = int(
            row.get(
                "year_precision_count",
                0
            )
            or 0
        )

        other_count = (
            claim_count
            - day_count
            - month_count
            - year_count
        )

        precisions = []

        precisions.extend(
            ["day"] * day_count
        )

        precisions.extend(
            ["month"] * month_count
        )

        precisions.extend(
            ["year"] * year_count
        )

        precisions.extend(
            ["other"] * max(
                0,
                other_count
            )
        )

        pattern = classify_claim_pattern(
            preferred_count,
            normal_count,
            deprecated_count,
            dates,
            precisions
        )

        unique_date_count = len(
            set(dates)
        )

        if unique_date_count > 1:
            date_conflict = True
        else:
            date_conflict = False

        precision_conflict = (
            len(set(precisions)) > 1
        )

        multiple.append({
            "reep_id": row.get(
                "reep_id"
            ),
            "label": row.get(
                "label"
            ),
            "source_qid": row.get(
                "source_qid"
            ),
            "resolved_qid": row.get(
                "resolved_qid"
            ),
            "redirected": row.get(
                "redirected",
                False
            ),
            "dob_claim_count": claim_count,
            "dob_values": row.get(
                "dob_values",
                ""
            ),
            "unique_dob_count": unique_date_count,
            "date_conflict": date_conflict,
            "precision_conflict": precision_conflict,
            "day_precision_count": day_count,
            "month_precision_count": month_count,
            "year_precision_count": year_count,
            "other_precision_count": max(
                0,
                other_count
            ),
            "preferred_claim_count": preferred_count,
            "normal_claim_count": normal_count,
            "deprecated_claim_count": deprecated_count,
            "classification": pattern
        })

        total_claims += claim_count

    # --------------------------------------------------------
    # Counters
    # --------------------------------------------------------

    classification_counts = Counter(
        row["classification"]
        for row in multiple
    )

    date_conflicts = sum(
        1
        for row in multiple
        if row["date_conflict"]
    )

    precision_conflicts = sum(
        1
        for row in multiple
        if row["precision_conflict"]
    )

    preferred_cases = sum(
        1
        for row in multiple
        if row["preferred_claim_count"] > 0
    )

    normal_cases = sum(
        1
        for row in multiple
        if row["normal_claim_count"] > 0
    )

    deprecated_cases = sum(
        1
        for row in multiple
        if row["deprecated_claim_count"] > 0
    )

    # --------------------------------------------------------
    # Write CSV
    # --------------------------------------------------------

    fieldnames = [
        "reep_id",
        "label",
        "source_qid",
        "resolved_qid",
        "redirected",
        "dob_claim_count",
        "dob_values",
        "unique_dob_count",
        "date_conflict",
        "precision_conflict",
        "day_precision_count",
        "month_precision_count",
        "year_precision_count",
        "other_precision_count",
        "preferred_claim_count",
        "normal_claim_count",
        "deprecated_claim_count",
        "classification"
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(multiple)

    # --------------------------------------------------------
    # Write JSON
    # --------------------------------------------------------

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            multiple,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("=" * 70)
    print("MULTIPLE-P569 SUMMARY")
    print("=" * 70)

    print(
        f"Players with multiple P569: "
        f"{len(multiple):,}"
    )

    print(
        f"Total P569 claims in these players: "
        f"{total_claims:,}"
    )

    print()

    print(
        f"Cases with different DOB dates: "
        f"{date_conflicts:,}"
    )

    print(
        f"Cases with mixed precision: "
        f"{precision_conflicts:,}"
    )

    print()

    print(
        f"Cases with preferred claims: "
        f"{preferred_cases:,}"
    )

    print(
        f"Cases with normal claims: "
        f"{normal_cases:,}"
    )

    print(
        f"Cases with deprecated claims: "
        f"{deprecated_cases:,}"
    )

    print()

    print("-" * 70)
    print("CLASSIFICATION")
    print("-" * 70)

    for name, count in sorted(
        classification_counts.items(),
        key=lambda x: (-x[1], x[0])
    ):
        print(
            f"{name:<45} {count:>8,}"
        )

    print()

    print("-" * 70)
    print("OUTPUT")
    print("-" * 70)

    print(
        f"CSV:  {OUTPUT_CSV}"
    )

    print(
        f"JSON: {OUTPUT_JSON}"
    )

    print()

    print(
        "No REEP database changes were made."
    )

    print("=" * 70)


if __name__ == "__main__":
    main()