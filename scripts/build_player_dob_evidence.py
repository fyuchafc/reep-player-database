import json
import os
import duckdb
from collections import Counter

# ============================================================
# REEP v1.1 — BUILD PLAYER DOB EVIDENCE
#
# READ-ONLY SOURCE
#
# Creates a derived DOB evidence layer from the completed
# Wikidata GraphQL audit.
#
# DOES NOT MODIFY:
#   - original REEP source database
#   - frozen v1.0.0 master database
#
# OUTPUT:
#   output\reep-player-dob-evidence.duckdb
#   output\reep-player-dob-evidence-build-report.json
# ============================================================


# ============================================================
# PATHS
# ============================================================

SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main\data"
    r"\reep-register-v1.duckdb"
)

GRAPHQL_PROGRESS = os.path.join(
    "output",
    "reep-wikidata-dob-graphql-progress.json"
)

OUTPUT_DB = os.path.join(
    "output",
    "reep-player-dob-evidence.duckdb"
)

OUTPUT_REPORT = os.path.join(
    "output",
    "reep-player-dob-evidence-build-report.json"
)


# ============================================================
# HELPERS
# ============================================================

def precision_name(value):
    """
    Wikidata time precision:
        11 = day
        10 = month
         9 = year
    """

    try:
        value = int(value)
    except (TypeError, ValueError):
        return "other"

    if value == 11:
        return "day"

    if value == 10:
        return "month"

    if value == 9:
        return "year"

    return "other"


def rank_name(value):
    """
    Normalize Wikidata statement rank.
    """

    value = str(value).upper()

    if value == "PREFERRED":
        return "preferred"

    if value == "NORMAL":
        return "normal"

    if value == "DEPRECATED":
        return "deprecated"

    return "other"


def classify_claims(claims):
    """
    Determine whether available P569 claims can safely
    produce a canonical DOB.

    We NEVER guess between conflicting dates.
    """

    if not claims:
        return {
            "status": "no_dob",
            "dob": None,
            "precision": None,
            "reason": "no_p569"
        }

    dates = sorted(
        set(
            c.get("dob")
            for c in claims
            if c.get("dob")
        )
    )

    preferred_dates = sorted(
        set(
            c.get("dob")
            for c in claims
            if rank_name(c.get("rank")) == "preferred"
            and c.get("dob")
        )
    )

    normal_dates = sorted(
        set(
            c.get("dob")
            for c in claims
            if rank_name(c.get("rank")) == "normal"
            and c.get("dob")
        )
    )

    deprecated_dates = sorted(
        set(
            c.get("dob")
            for c in claims
            if rank_name(c.get("rank")) == "deprecated"
            and c.get("dob")
        )
    )

    # ========================================================
    # ONE CLAIM
    # ========================================================

    if len(claims) == 1:

        claim = claims[0]

        dob = claim.get("dob")

        if not dob:
            return {
                "status": "unresolved",
                "dob": None,
                "precision": None,
                "reason": "missing_dob_value"
            }

        precision = precision_name(
            claim.get("precision")
        )

        rank = rank_name(
            claim.get("rank")
        )

        if precision == "day":

            if rank == "preferred":
                status = "supported_preferred"

            elif rank == "normal":
                status = "supported"

            elif rank == "deprecated":
                status = "deprecated_only"

            else:
                status = "unresolved"

            return {
                "status": status,
                "dob": dob,
                "precision": precision,
                "reason": "single_p569"
            }

        return {
            "status": "partial_precision",
            "dob": dob,
            "precision": precision,
            "reason": "single_p569_non_day_precision"
        }

    # ========================================================
    # MULTIPLE CLAIMS — SAME DATE
    # ========================================================

    if len(dates) == 1:

        dob = dates[0]

        precisions = {
            precision_name(c.get("precision"))
            for c in claims
            if c.get("dob") == dob
        }

        if "day" in precisions:
            precision = "day"

        elif "month" in precisions:
            precision = "month"

        elif "year" in precisions:
            precision = "year"

        else:
            precision = "other"

        if preferred_dates:
            return {
                "status": "supported_preferred",
                "dob": dob,
                "precision": precision,
                "reason": "multiple_claims_same_date"
            }

        if normal_dates:
            return {
                "status": "supported",
                "dob": dob,
                "precision": precision,
                "reason": "multiple_claims_same_date"
            }

        return {
            "status": "deprecated_only",
            "dob": dob,
            "precision": precision,
            "reason": "multiple_claims_same_date_deprecated"
        }

    # ========================================================
    # MULTIPLE CLAIMS — ONE PREFERRED DATE
    # ========================================================

    if len(preferred_dates) == 1:

        dob = preferred_dates[0]

        preferred_claims = [
            c
            for c in claims
            if rank_name(c.get("rank")) == "preferred"
            and c.get("dob") == dob
        ]

        precisions = {
            precision_name(c.get("precision"))
            for c in preferred_claims
        }

        if "day" in precisions:
            precision = "day"

        elif "month" in precisions:
            precision = "month"

        elif "year" in precisions:
            precision = "year"

        else:
            precision = "other"

        return {
            "status": "supported_preferred",
            "dob": dob,
            "precision": precision,
            "reason": "one_preferred_date"
        }

    # ========================================================
    # MULTIPLE PREFERRED DATES
    # ========================================================

    if len(preferred_dates) > 1:

        return {
            "status": "conflicted",
            "dob": None,
            "precision": None,
            "reason": "multiple_preferred_dates"
        }

    # ========================================================
    # NORMAL + DEPRECATED
    # ========================================================

    if normal_dates and deprecated_dates:

        return {
            "status": "conflicted",
            "dob": None,
            "precision": None,
            "reason": "normal_plus_deprecated"
        }

    # ========================================================
    # MULTIPLE NORMAL DATES
    # ========================================================

    if len(normal_dates) > 1:

        return {
            "status": "conflicted",
            "dob": None,
            "precision": None,
            "reason": "multiple_normal_dates"
        }

    # ========================================================
    # ONE NORMAL DATE
    # ========================================================

    if len(normal_dates) == 1:

        dob = normal_dates[0]

        normal_claims = [
            c
            for c in claims
            if rank_name(c.get("rank")) == "normal"
            and c.get("dob") == dob
        ]

        precisions = {
            precision_name(c.get("precision"))
            for c in normal_claims
        }

        if "day" in precisions:
            precision = "day"

        elif "month" in precisions:
            precision = "month"

        elif "year" in precisions:
            precision = "year"

        else:
            precision = "other"

        return {
            "status": "supported",
            "dob": dob,
            "precision": precision,
            "reason": "single_normal_date"
        }

    # ========================================================
    # DEPRECATED ONLY
    # ========================================================

    if len(deprecated_dates) == 1:

        return {
            "status": "deprecated_only",
            "dob": deprecated_dates[0],
            "precision": "other",
            "reason": "deprecated_only"
        }

    # ========================================================
    # FALLBACK
    # ========================================================

    return {
        "status": "unresolved",
        "dob": None,
        "precision": None,
        "reason": "unresolved_claim_pattern"
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print("REEP v1.1 — BUILD PLAYER DOB EVIDENCE")
    print("=" * 70)
    print()

    # ========================================================
    # CHECK FILES
    # ========================================================

    if not os.path.exists(SOURCE_DB):

        print("ERROR: Source REEP database not found.")
        print(SOURCE_DB)
        return

    if not os.path.exists(GRAPHQL_PROGRESS):

        print("ERROR: Wikidata GraphQL progress file not found.")
        print(GRAPHQL_PROGRESS)
        return

    # ========================================================
    # READ SOURCE REEP DATABASE
    # ========================================================

    print("Opening source REEP database READ-ONLY...")
    print()

    con = duckdb.connect(
        SOURCE_DB,
        read_only=True
    )

    print("Reading REEP player → QID mappings...")

    query = """
        SELECT DISTINCT
            p.reep_id,
            p.label,
            p.status,
            p.gender,
            e.corroboration_grade,
            e.corroboration_count,
            ol.qid
        FROM players p
        INNER JOIN entities e
            ON e.reep_id = p.reep_id
        INNER JOIN overlay_links ol
            ON ol.reep_id = p.reep_id
        WHERE
            ol.qid IS NOT NULL
            AND TRIM(ol.qid) <> ''
            AND LOWER(TRIM(ol.dob_check)) = 'dob-agrees'
            AND e.entity_type = 'player'
        ORDER BY
            ol.qid,
            p.reep_id
    """

    rows = con.execute(
        query
    ).fetchall()

    con.close()

    print(
        f"REEP player/QID mappings: {len(rows):,}"
    )

    print()

    # ========================================================
    # READ WIKIDATA RESULTS
    # ========================================================

    print("Reading Wikidata GraphQL results...")

    with open(
        GRAPHQL_PROGRESS,
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
    # DELETE OLD DERIVED DATABASE
    # ========================================================

    if os.path.exists(OUTPUT_DB):

        print(
            "Existing derived DOB database found."
        )

        print(
            "Replacing it with a fresh build..."
        )

        os.remove(
            OUTPUT_DB
        )

        print()

    # ========================================================
    # CREATE OUTPUT DATABASE
    # ========================================================

    out = duckdb.connect(
        OUTPUT_DB
    )

    # ========================================================
    # RAW CLAIM TABLE
    # ========================================================

    out.execute("""
        CREATE TABLE player_dob_claims (
            reep_id VARCHAR,
            label VARCHAR,
            status VARCHAR,
            gender VARCHAR,
            corroboration_grade VARCHAR,
            corroboration_count INTEGER,

            source_qid VARCHAR,
            resolved_qid VARCHAR,
            redirected BOOLEAN,

            dob VARCHAR,
            precision VARCHAR,
            rank VARCHAR,

            source VARCHAR
        )
    """)

    # ========================================================
    # CANONICAL PLAYER DOB TABLE
    # ========================================================

    out.execute("""
        CREATE TABLE player_dob (
            reep_id VARCHAR PRIMARY KEY,

            label VARCHAR,
            status VARCHAR,
            gender VARCHAR,

            corroboration_grade VARCHAR,
            corroboration_count INTEGER,

            dob VARCHAR,
            dob_precision VARCHAR,
            dob_status VARCHAR,
            evidence_reason VARCHAR,

            source_qid VARCHAR,
            resolved_qid VARCHAR,
            redirected BOOLEAN,

            claim_count INTEGER,
            preferred_claim_count INTEGER,
            normal_claim_count INTEGER,
            deprecated_claim_count INTEGER,

            source VARCHAR
        )
    """)

    # ========================================================
    # COUNTERS
    # ========================================================

    claim_count_distribution = Counter()
    status_counter = Counter()
    precision_counter = Counter()

    claim_rows = []
    player_rows = []

    skipped_missing_qid_results = 0

    # ========================================================
    # PROCESS PLAYER/QID MAPPINGS
    # ========================================================

    for (
        reep_id,
        label,
        status,
        gender,
        corroboration_grade,
        corroboration_count,
        qid
    ) in rows:

        result = results.get(qid)

        if result is None:

            skipped_missing_qid_results += 1

            continue

        resolved_qid = result.get(
            "resolved_qid",
            qid
        )

        redirected = bool(
            result.get(
                "redirected",
                False
            )
        )

        claims = result.get(
            "dob_claims",
            []
        )

        claim_count_distribution[
            len(claims)
        ] += 1

        preferred_count = 0
        normal_count = 0
        deprecated_count = 0

        # ====================================================
        # RAW CLAIMS
        # ====================================================

        for claim in claims:

            rank = rank_name(
                claim.get("rank")
            )

            if rank == "preferred":

                preferred_count += 1

            elif rank == "normal":

                normal_count += 1

            elif rank == "deprecated":

                deprecated_count += 1

            # IMPORTANT:
            # Exactly 13 values for exactly 13 columns.
            claim_rows.append(
                (
                    reep_id,
                    label,
                    status,
                    gender,
                    corroboration_grade,
                    corroboration_count,

                    qid,
                    resolved_qid,
                    redirected,

                    claim.get("dob"),
                    precision_name(
                        claim.get("precision")
                    ),
                    rank,

                    "wikidata"
                )
            )

        # ====================================================
        # CANONICAL CLASSIFICATION
        # ====================================================

        classification = classify_claims(
            claims
        )

        dob_status = classification[
            "status"
        ]

        status_counter[
            dob_status
        ] += 1

        if classification["precision"]:

            precision_counter[
                classification["precision"]
            ] += 1

        player_rows.append(
            (
                reep_id,
                label,
                status,
                gender,

                corroboration_grade,
                corroboration_count,

                classification["dob"],
                classification["precision"],
                dob_status,
                classification["reason"],

                qid,
                resolved_qid,
                redirected,

                len(claims),
                preferred_count,
                normal_count,
                deprecated_count,

                "wikidata"
            )
        )

    # ========================================================
    # INSERT RAW CLAIMS
    # ========================================================

    if claim_rows:

        out.executemany(
            """
            INSERT INTO player_dob_claims (
                reep_id,
                label,
                status,
                gender,
                corroboration_grade,
                corroboration_count,
                source_qid,
                resolved_qid,
                redirected,
                dob,
                precision,
                rank,
                source
            )
            VALUES (
                ?,?,?,?,?,?,
                ?,?,?,?,
                ?,?,?
            )
            """,
            claim_rows
        )

    # ========================================================
    # INSERT CANONICAL PLAYER DATA
    # ========================================================

    if player_rows:

        out.executemany(
            """
            INSERT INTO player_dob (
                reep_id,
                label,
                status,
                gender,
                corroboration_grade,
                corroboration_count,
                dob,
                dob_precision,
                dob_status,
                evidence_reason,
                source_qid,
                resolved_qid,
                redirected,
                claim_count,
                preferred_claim_count,
                normal_claim_count,
                deprecated_claim_count,
                source
            )
            VALUES (
                ?,?,?,?,?,?,
                ?,?,?,?,
                ?,?,?,
                ?,?,?,?,
                ?
            )
            """,
            player_rows
        )

    # ========================================================
    # INDEXES
    # ========================================================

    out.execute("""
        CREATE INDEX idx_player_dob_reep_id
        ON player_dob(reep_id)
    """)

    out.execute("""
        CREATE INDEX idx_player_dob_dob
        ON player_dob(dob)
    """)

    out.execute("""
        CREATE INDEX idx_player_dob_status
        ON player_dob(dob_status)
    """)

    out.execute("""
        CREATE INDEX idx_player_dob_claims_reep_id
        ON player_dob_claims(reep_id)
    """)

    out.execute("""
        CREATE INDEX idx_player_dob_claims_qid
        ON player_dob_claims(source_qid)
    """)

    # ========================================================
    # VALIDATION
    # ========================================================

    total_players = out.execute(
        """
        SELECT COUNT(*)
        FROM player_dob
        """
    ).fetchone()[0]

    total_claim_rows = out.execute(
        """
        SELECT COUNT(*)
        FROM player_dob_claims
        """
    ).fetchone()[0]

    duplicate_players = out.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT reep_id
            FROM player_dob
            GROUP BY reep_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    orphan_claims = out.execute(
        """
        SELECT COUNT(*)
        FROM player_dob_claims c
        LEFT JOIN player_dob p
            ON c.reep_id = p.reep_id
        WHERE p.reep_id IS NULL
        """
    ).fetchone()[0]

    null_player_ids = out.execute(
        """
        SELECT COUNT(*)
        FROM player_dob
        WHERE
            reep_id IS NULL
            OR TRIM(reep_id) = ''
        """
    ).fetchone()[0]

    null_claim_player_ids = out.execute(
        """
        SELECT COUNT(*)
        FROM player_dob_claims
        WHERE
            reep_id IS NULL
            OR TRIM(reep_id) = ''
        """
    ).fetchone()[0]

    # ========================================================
    # METADATA
    # ========================================================

    out.execute(
        """
        CREATE TABLE database_metadata (
            key VARCHAR,
            value VARCHAR
        )
        """
    )

    metadata = [
        (
            "layer",
            "REEP v1.1 DOB evidence"
        ),
        (
            "source",
            "Wikidata P569 via GraphQL"
        ),
        (
            "source_audit",
            "reep-wikidata-dob-graphql-audit"
        ),
        (
            "source_database",
            "reep-register-v1.duckdb"
        ),
        (
            "identity_key",
            "reep_id"
        ),
        (
            "generated_by",
            "build_player_dob_evidence.py"
        ),
        (
            "purpose",
            "Derived DOB evidence layer for REEP v1.1"
        ),
        (
            "v1_policy",
            "Frozen v1.0.0 master is not modified"
        )
    ]

    out.executemany(
        """
        INSERT INTO database_metadata
        VALUES (?,?)
        """,
        metadata
    )

    out.close()

    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    validation_pass = (
        duplicate_players == 0
        and orphan_claims == 0
        and null_player_ids == 0
        and null_claim_player_ids == 0
        and skipped_missing_qid_results == 0
    )

    # ========================================================
    # BUILD REPORT
    # ========================================================

    report = {
        "status":
            "PASS"
            if validation_pass
            else "FAIL",

        "layer":
            "REEP v1.1 DOB evidence",

        "source":
            "Wikidata P569 via GraphQL",

        "reep_player_qid_mappings":
            len(rows),

        "output_players":
            total_players,

        "output_claim_rows":
            total_claim_rows,

        "skipped_missing_qid_results":
            skipped_missing_qid_results,

        "duplicate_player_ids":
            duplicate_players,

        "orphan_claim_rows":
            orphan_claims,

        "null_player_ids":
            null_player_ids,

        "null_claim_player_ids":
            null_claim_player_ids,

        "claim_count_distribution":
            dict(
                sorted(
                    claim_count_distribution.items()
                )
            ),

        "dob_status_distribution":
            dict(
                status_counter
            ),

        "canonical_precision_distribution":
            dict(
                precision_counter
            ),

        "output_database":
            OUTPUT_DB
    }

    with open(
        OUTPUT_REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    # ========================================================
    # DISPLAY RESULTS
    # ========================================================

    print("=" * 70)
    print("BUILD COMPLETE")
    print("=" * 70)
    print()

    print(
        f"REEP player/QID mappings:       {len(rows):,}"
    )

    print(
        f"Output player rows:             {total_players:,}"
    )

    print(
        f"Output DOB claim rows:          {total_claim_rows:,}"
    )

    print(
        f"Skipped missing QID results:    {skipped_missing_qid_results:,}"
    )

    print()

    print("=" * 70)
    print("DOB STATUS DISTRIBUTION")
    print("=" * 70)

    for name, count in sorted(
        status_counter.items()
    ):

        print(
            f"{name:<32}{count:>10,}"
        )

    print()

    print("=" * 70)
    print("CANONICAL PRECISION")
    print("=" * 70)

    for name, count in sorted(
        precision_counter.items()
    ):

        print(
            f"{name:<32}{count:>10,}"
        )

    print()

    print("=" * 70)
    print("VALIDATION")
    print("=" * 70)

    print(
        f"Duplicate player IDs:           {duplicate_players:,}"
    )

    print(
        f"Orphan claim rows:               {orphan_claims:,}"
    )

    print(
        f"NULL/empty player IDs:           {null_player_ids:,}"
    )

    print(
        f"NULL/empty claim player IDs:     {null_claim_player_ids:,}"
    )

    print(
        f"Missing QID result mappings:     {skipped_missing_qid_results:,}"
    )

    print()

    if validation_pass:

        print("FINAL STATUS: PASS")

    else:

        print("FINAL STATUS: FAIL")

    print()

    print(
        f"DATABASE: {OUTPUT_DB}"
    )

    print(
        f"REPORT:   {OUTPUT_REPORT}"
    )

    print()

    print(
        "No source database was modified."
    )

    print(
        "Frozen v1.0.0 master was not modified."
    )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()