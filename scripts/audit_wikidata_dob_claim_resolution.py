import json
import os
from collections import Counter


# ============================================================
# REEP — WIKIDATA DOB CLAIM RESOLUTION AUDIT
# ============================================================
#
# READ-ONLY.
#
# Uses the completed GraphQL progress file because it contains
# the individual P569 claims together with their ranks.
#
# This script DOES NOT select or write canonical DOBs.
# It only determines whether Wikidata's claim ranks provide
# a safe basis for selecting one.
# ============================================================


PROGRESS_FILE = os.path.join(
    "output",
    "reep-wikidata-dob-graphql-progress.json"
)

OUTPUT_JSON = os.path.join(
    "output",
    "reep-wikidata-dob-claim-resolution.json"
)


def rank_priority(rank):
    """
    Higher number = stronger Wikidata rank.
    """
    rank = str(rank).upper()

    if rank == "PREFERRED":
        return 3

    if rank == "NORMAL":
        return 2

    if rank == "DEPRECATED":
        return 1

    return 0


def classify_case(claims):

    if not claims:
        return "no_claims"

    dates = [
        c.get("dob")
        for c in claims
        if c.get("dob")
    ]

    unique_dates = sorted(set(dates))

    ranks = [
        str(c.get("rank", "")).upper()
        for c in claims
    ]

    preferred_dates = sorted(set(
        c.get("dob")
        for c in claims
        if str(c.get("rank", "")).upper() == "PREFERRED"
        and c.get("dob")
    ))

    normal_dates = sorted(set(
        c.get("dob")
        for c in claims
        if str(c.get("rank", "")).upper() == "NORMAL"
        and c.get("dob")
    ))

    deprecated_dates = sorted(set(
        c.get("dob")
        for c in claims
        if str(c.get("rank", "")).upper() == "DEPRECATED"
        and c.get("dob")
    ))

    # --------------------------------------------------------
    # Same date repeated
    # --------------------------------------------------------

    if len(unique_dates) == 1:

        if "PREFERRED" in ranks:
            return "same_date_preferred"

        if "NORMAL" in ranks:
            return "same_date_normal"

        return "same_date_deprecated"

    # --------------------------------------------------------
    # Different dates
    # --------------------------------------------------------

    if preferred_dates:

        # One preferred date only.
        if len(preferred_dates) == 1:
            return "one_preferred_date"

        # More than one preferred date.
        return "multiple_preferred_dates"

    # No preferred claims.
    if normal_dates:

        if deprecated_dates:
            return "normal_plus_deprecated_no_preferred"

        return "multiple_normal_dates"

    return "deprecated_dates_only"


def main():

    print()
    print("=" * 70)
    print("WIKIDATA DOB CLAIM RESOLUTION AUDIT")
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

    cases = []

    # ========================================================
    # Analyse every QID result
    # ========================================================

    for qid, result in results.items():

        claims = result.get(
            "dob_claims",
            []
        )

        if len(claims) <= 1:
            continue

        dates = sorted(set(
            c.get("dob")
            for c in claims
            if c.get("dob")
        ))

        preferred = [
            c for c in claims
            if str(
                c.get("rank", "")
            ).upper() == "PREFERRED"
        ]

        normal = [
            c for c in claims
            if str(
                c.get("rank", "")
            ).upper() == "NORMAL"
        ]

        deprecated = [
            c for c in claims
            if str(
                c.get("rank", "")
            ).upper() == "DEPRECATED"
        ]

        preferred_dates = sorted(set(
            c.get("dob")
            for c in preferred
            if c.get("dob")
        ))

        normal_dates = sorted(set(
            c.get("dob")
            for c in normal
            if c.get("dob")
        ))

        deprecated_dates = sorted(set(
            c.get("dob")
            for c in deprecated
            if c.get("dob")
        ))

        case = classify_case(claims)

        # ----------------------------------------------------
        # Determine whether rank uniquely identifies one date.
        # ----------------------------------------------------

        rank_resolves = False
        proposed_date = None

        if len(preferred_dates) == 1:
            rank_resolves = True
            proposed_date = preferred_dates[0]

        elif len(preferred_dates) > 1:
            rank_resolves = False

        elif len(dates) == 1:
            rank_resolves = True
            proposed_date = dates[0]

        cases.append({
            "source_qid": qid,
            "resolved_qid": result.get(
                "resolved_qid"
            ),
            "redirected": result.get(
                "redirected",
                False
            ),
            "claim_count": len(claims),
            "dates": dates,
            "preferred_dates": preferred_dates,
            "normal_dates": normal_dates,
            "deprecated_dates": deprecated_dates,
            "rank_resolves": rank_resolves,
            "proposed_date": proposed_date,
            "classification": case,
            "claims": claims
        })

    # ========================================================
    # Summary counters
    # ========================================================

    classification_counts = Counter(
        c["classification"]
        for c in cases
    )

    resolvable = [
        c for c in cases
        if c["rank_resolves"]
    ]

    unresolved = [
        c for c in cases
        if not c["rank_resolves"]
    ]

    one_preferred = [
        c for c in cases
        if c["classification"]
        == "one_preferred_date"
    ]

    multiple_preferred = [
        c for c in cases
        if c["classification"]
        == "multiple_preferred_dates"
    ]

    normal_only = [
        c for c in cases
        if c["classification"]
        == "multiple_normal_dates"
    ]

    normal_deprecated = [
        c for c in cases
        if c["classification"]
        == "normal_plus_deprecated_no_preferred"
    ]

    same_date = [
        c for c in cases
        if c["classification"].startswith(
            "same_date_"
        )
    ]

    deprecated_only = [
        c for c in cases
        if c["classification"]
        == "deprecated_dates_only"
    ]

    # ========================================================
    # Print summary
    # ========================================================

    print("=" * 70)
    print("CLAIM-LEVEL RESOLUTION SUMMARY")
    print("=" * 70)

    print(
        f"Multiple-P569 QIDs: "
        f"{len(cases):,}"
    )

    print()

    print(
        f"Cases resolvable by one preferred date: "
        f"{len(one_preferred):,}"
    )

    print(
        f"Cases with multiple preferred dates: "
        f"{len(multiple_preferred):,}"
    )

    print(
        f"Cases with multiple normal dates: "
        f"{len(normal_only):,}"
    )

    print(
        f"Normal + deprecated, no preferred: "
        f"{len(normal_deprecated):,}"
    )

    print(
        f"Same date repeated: "
        f"{len(same_date):,}"
    )

    print(
        f"Deprecated-only cases: "
        f"{len(deprecated_only):,}"
    )

    print()

    print(
        f"Potentially resolvable by rank: "
        f"{len(resolvable):,}"
    )

    print(
        f"Still requiring additional policy: "
        f"{len(unresolved):,}"
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

    # ========================================================
    # Show unresolved examples
    # ========================================================

    print()
    print("-" * 70)
    print("UNRESOLVED EXAMPLES")
    print("-" * 70)

    for case in unresolved[:20]:

        print()
        print(
            f"QID: {case['source_qid']}"
        )

        print(
            f"Resolved QID: "
            f"{case['resolved_qid']}"
        )

        print(
            f"Classification: "
            f"{case['classification']}"
        )

        print(
            f"Dates: "
            f"{', '.join(case['dates'])}"
        )

        print(
            f"Preferred: "
            f"{', '.join(case['preferred_dates']) or 'NONE'}"
        )

        print(
            f"Normal: "
            f"{', '.join(case['normal_dates']) or 'NONE'}"
        )

        print(
            f"Deprecated: "
            f"{', '.join(case['deprecated_dates']) or 'NONE'}"
        )

    # ========================================================
    # Save detailed JSON
    # ========================================================

    output = {
        "generated_at": __import__(
            "datetime"
        ).datetime.now(
            __import__(
                "datetime"
            ).timezone.utc
        ).isoformat(),

        "total_multiple_p569": len(cases),

        "resolvable_by_rank": len(resolvable),

        "unresolved_by_rank": len(unresolved),

        "classification_counts": dict(
            classification_counts
        ),

        "cases": cases
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

    print()
    print("=" * 70)
    print("OUTPUT")
    print("=" * 70)

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