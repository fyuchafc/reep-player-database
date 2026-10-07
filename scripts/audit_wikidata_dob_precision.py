import json
import os
from collections import Counter


# ============================================================
# REEP — WIKIDATA DOB PRECISION & RANK AUDIT
# ============================================================
#
# READ-ONLY.
#
# Analyses all completed Wikidata DOB results.
#
# Purpose:
#   Establish final DOB coverage by:
#     - claim count
#     - precision
#     - rank
#     - multiple-claim status
#     - redirect status
#
# This script DOES NOT:
#   - modify the REEP database
#   - modify v1.0.0
#   - select canonical DOBs
#   - discard any evidence
# ============================================================


PROGRESS_FILE = os.path.join(
    "output",
    "reep-wikidata-dob-graphql-progress.json"
)

OUTPUT_JSON = os.path.join(
    "output",
    "reep-wikidata-dob-precision-audit.json"
)


def rank_name(rank):
    rank = str(rank).upper()

    if rank == "PREFERRED":
        return "preferred"

    if rank == "NORMAL":
        return "normal"

    if rank == "DEPRECATED":
        return "deprecated"

    return "other"


def precision_name(value):
    if value == 11:
        return "day"

    if value == 10:
        return "month"

    if value == 9:
        return "year"

    return "other"


def main():

    print()
    print("=" * 70)
    print("WIKIDATA DOB PRECISION & RANK AUDIT")
    print("=" * 70)
    print()

    if not os.path.exists(PROGRESS_FILE):
        print("ERROR:")
        print(
            f"Progress file not found: {PROGRESS_FILE}"
        )
        return

    print(
        f"Reading: {PROGRESS_FILE}"
    )

    with open(
        PROGRESS_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        progress = json.load(f)

    results = progress.get(
        "results",
        {}
    )

    print(
        f"QID results available: {len(results):,}"
    )

    print()

    # ========================================================
    # Counters
    # ========================================================

    entities_found = 0
    entities_without_p569 = 0

    total_claims = 0

    single_claim = 0
    multiple_claims = 0

    redirected = 0

    precision_counts = Counter()
    rank_counts = Counter()

    single_precision = Counter()
    single_rank = Counter()

    multiple_precision_patterns = Counter()
    multiple_rank_patterns = Counter()

    # Candidate categories
    one_preferred = 0
    one_normal = 0
    one_deprecated = 0

    same_date_multiple = 0
    multiple_preferred = 0
    multiple_normal = 0
    normal_plus_deprecated = 0
    deprecated_only = 0

    # ========================================================
    # Analyse
    # ========================================================

    for source_qid, result in results.items():

        if result.get("entity_found"):
            entities_found += 1

        if result.get("redirected"):
            redirected += 1

        claims = result.get(
            "dob_claims",
            []
        )

        if not claims:
            entities_without_p569 += 1
            continue

        total_claims += len(claims)

        # ----------------------------------------------------
        # Claim-level precision/rank
        # ----------------------------------------------------

        for claim in claims:

            precision = claim.get(
                "precision"
            )

            rank = rank_name(
                claim.get("rank")
            )

            precision_counts[
                precision_name(precision)
            ] += 1

            rank_counts[
                rank
            ] += 1

        # ----------------------------------------------------
        # Single claim
        # ----------------------------------------------------

        if len(claims) == 1:

            single_claim += 1

            claim = claims[0]

            precision = precision_name(
                claim.get("precision")
            )

            rank = rank_name(
                claim.get("rank")
            )

            single_precision[
                precision
            ] += 1

            single_rank[
                rank
            ] += 1

            if rank == "preferred":
                one_preferred += 1

            elif rank == "normal":
                one_normal += 1

            elif rank == "deprecated":
                one_deprecated += 1

            continue

        # ----------------------------------------------------
        # Multiple claims
        # ----------------------------------------------------

        multiple_claims += 1

        dates = sorted(set(
            c.get("dob")
            for c in claims
            if c.get("dob")
        ))

        ranks = [
            rank_name(
                c.get("rank")
            )
            for c in claims
        ]

        precisions = [
            precision_name(
                c.get("precision")
            )
            for c in claims
        ]

        # Precision pattern
        precision_pattern = "+".join(
            sorted(set(precisions))
        )

        multiple_precision_patterns[
            precision_pattern
        ] += 1

        # Rank pattern
        rank_pattern = "+".join(
            sorted(set(ranks))
        )

        multiple_rank_patterns[
            rank_pattern
        ] += 1

        # Same date repeated
        if len(dates) == 1:
            same_date_multiple += 1

        # Preferred
        preferred_dates = set(
            c.get("dob")
            for c in claims
            if rank_name(
                c.get("rank")
            ) == "preferred"
        )

        normal_dates = set(
            c.get("dob")
            for c in claims
            if rank_name(
                c.get("rank")
            ) == "normal"
        )

        deprecated_dates = set(
            c.get("dob")
            for c in claims
            if rank_name(
                c.get("rank")
            ) == "deprecated"
        )

        if preferred_dates:
            if len(preferred_dates) > 1:
                multiple_preferred += 1

        elif normal_dates and deprecated_dates:
            normal_plus_deprecated += 1

        elif normal_dates:
            multiple_normal += 1

        elif deprecated_dates:
            deprecated_only += 1

    # ========================================================
    # Derived coverage
    # ========================================================

    day_claims = precision_counts["day"]
    month_claims = precision_counts["month"]
    year_claims = precision_counts["year"]
    other_claims = precision_counts["other"]

    exact_single_day = single_precision["day"]

    exact_or_resolvable_day = (
        exact_single_day
        + same_date_multiple
    )

    # ========================================================
    # Output
    # ========================================================

    output = {
        "total_qid_results": len(results),
        "entities_found": entities_found,
        "entities_without_p569": entities_without_p569,
        "total_p569_claims": total_claims,
        "single_claim_entities": single_claim,
        "multiple_claim_entities": multiple_claims,
        "redirected_entities": redirected,

        "precision_counts": dict(
            precision_counts
        ),

        "rank_counts": dict(
            rank_counts
        ),

        "single_claim_precision": dict(
            single_precision
        ),

        "single_claim_rank": dict(
            single_rank
        ),

        "multiple_precision_patterns": dict(
            multiple_precision_patterns
        ),

        "multiple_rank_patterns": dict(
            multiple_rank_patterns
        ),

        "resolution_categories": {
            "one_preferred": one_preferred,
            "one_normal": one_normal,
            "one_deprecated": one_deprecated,
            "same_date_multiple": same_date_multiple,
            "multiple_preferred": multiple_preferred,
            "multiple_normal": multiple_normal,
            "normal_plus_deprecated": normal_plus_deprecated,
            "deprecated_only": deprecated_only
        },

        "derived": {
            "day_precision_claims": day_claims,
            "month_precision_claims": month_claims,
            "year_precision_claims": year_claims,
            "other_precision_claims": other_claims,
            "single_claim_day_precision": exact_single_day,
            "single_or_same_date_day_precision": (
                exact_or_resolvable_day
            )
        }
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # Print report
    # ========================================================

    print("=" * 70)
    print("OVERALL")
    print("=" * 70)

    print(
        f"Entities found:                 "
        f"{entities_found:,}"
    )

    print(
        f"Entities without P569:          "
        f"{entities_without_p569:,}"
    )

    print(
        f"Total P569 claims:               "
        f"{total_claims:,}"
    )

    print(
        f"Single-P569 entities:            "
        f"{single_claim:,}"
    )

    print(
        f"Multiple-P569 entities:          "
        f"{multiple_claims:,}"
    )

    print(
        f"Redirected entities:             "
        f"{redirected:,}"
    )

    print()

    print("=" * 70)
    print("P569 PRECISION")
    print("=" * 70)

    print(
        f"Day precision:                   "
        f"{day_claims:,}"
    )

    print(
        f"Month precision:                 "
        f"{month_claims:,}"
    )

    print(
        f"Year precision:                  "
        f"{year_claims:,}"
    )

    print(
        f"Other precision:                 "
        f"{other_claims:,}"
    )

    print()

    print("=" * 70)
    print("P569 RANK")
    print("=" * 70)

    for name in [
        "preferred",
        "normal",
        "deprecated",
        "other"
    ]:

        print(
            f"{name.capitalize():<32}"
            f"{rank_counts[name]:>8,}"
        )

    print()

    print("=" * 70)
    print("SINGLE-P569 ENTITIES")
    print("=" * 70)

    print(
        f"Day precision:                   "
        f"{single_precision['day']:,}"
    )

    print(
        f"Month precision:                 "
        f"{single_precision['month']:,}"
    )

    print(
        f"Year precision:                  "
        f"{single_precision['year']:,}"
    )

    print(
        f"Other precision:                 "
        f"{single_precision['other']:,}"
    )

    print()

    print(
        f"Preferred:                       "
        f"{one_preferred:,}"
    )

    print(
        f"Normal:                          "
        f"{one_normal:,}"
    )

    print(
        f"Deprecated:                      "
        f"{one_deprecated:,}"
    )

    print()

    print("=" * 70)
    print("MULTIPLE-P569 RESOLUTION")
    print("=" * 70)

    print(
        f"Same date repeated:              "
        f"{same_date_multiple:,}"
    )

    print(
        f"One/more preferred dates:        "
        f"{multiple_preferred:,}"
    )

    print(
        f"Multiple normal dates:           "
        f"{multiple_normal:,}"
    )

    print(
        f"Normal + deprecated:             "
        f"{normal_plus_deprecated:,}"
    )

    print(
        f"Deprecated only:                 "
        f"{deprecated_only:,}"
    )

    print()

    print("=" * 70)
    print("MULTIPLE CLAIM PRECISION PATTERNS")
    print("=" * 70)

    for name, count in sorted(
        multiple_precision_patterns.items(),
        key=lambda x: (-x[1], x[0])
    ):

        print(
            f"{name:<32}{count:>8,}"
        )

    print()

    print("=" * 70)
    print("MULTIPLE CLAIM RANK PATTERNS")
    print("=" * 70)

    for name, count in sorted(
        multiple_rank_patterns.items(),
        key=lambda x: (-x[1], x[0])
    ):

        print(
            f"{name:<32}{count:>8,}"
        )

    print()

    print("=" * 70)
    print("DERIVED")
    print("=" * 70)

    print(
        f"Single-claim day precision:      "
        f"{exact_single_day:,}"
    )

    print(
        f"Single/same-date day precision:  "
        f"{exact_or_resolvable_day:,}"
    )

    print()

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