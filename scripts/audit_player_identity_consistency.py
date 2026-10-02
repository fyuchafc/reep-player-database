import os
import csv
import json
from datetime import datetime, timezone

import duckdb


# ============================================================
# PATHS
# ============================================================

SOURCE_ROOT = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
)

REPO_ROOT = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\reep-player-database-main"
)

DB_PATH = os.path.join(
    SOURCE_ROOT,
    "data",
    "reep-register-v1.duckdb"
)

OUTPUT_DIR = os.path.join(
    REPO_ROOT,
    "output"
)

CSV_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-identity-consistency.csv"
)

JSON_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-identity-consistency.json"
)


# ============================================================
# HELPERS
# ============================================================

def normalize_id(value):
    if value is None:
        return None

    value = str(value).strip()

    return value if value else None


def normalize_label(value):
    if value is None:
        return ""

    return " ".join(
        str(value).strip().lower().split()
    )


def print_section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def yes_no(value):
    return "yes" if value else "no"


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    print("=" * 70)
    print("REEP PLAYER IDENTITY CONSISTENCY AUDIT")
    print("=" * 70)

    print()
    print(
        "READ-ONLY — source database will NOT be modified."
    )

    print()
    print("Source database:")
    print(DB_PATH)

    if not os.path.exists(DB_PATH):

        raise FileNotFoundError(
            f"Source database not found:\n{DB_PATH}"
        )

    print()
    print(
        "Opening REEP database READ-ONLY..."
    )

    con = duckdb.connect(
        DB_PATH,
        read_only=True
    )

    print(
        "Connected successfully."
    )

    # ========================================================
    # REQUIRED TABLES
    # ========================================================

    print_section(
        "CHECKING REQUIRED TABLES"
    )

    required_tables = {
        "players",
        "entities",
        "overlay_links",
        "overlay_xids",
        "aliases",
        "overlay_aliases",
        "redirects",
    }

    tables = {
        row[0]
        for row in con.execute(
            "SHOW TABLES"
        ).fetchall()
    }

    missing_tables = (
        required_tables - tables
    )

    for table in sorted(required_tables):

        if table in tables:
            print(
                f"  {table:<20} FOUND"
            )

        else:
            print(
                f"  {table:<20} MISSING"
            )

    if missing_tables:

        raise RuntimeError(
            "Missing required tables: "
            + ", ".join(
                sorted(missing_tables)
            )
        )

    # ========================================================
    # PLAYER SCHEMA
    # ========================================================

    print_section(
        "CHECKING PLAYER SCHEMA"
    )

    player_columns = {
        row[0]
        for row in con.execute(
            "DESCRIBE players"
        ).fetchall()
    }

    required_player_columns = {
        "reep_id",
        "label",
        "status",
        "gender",
    }

    missing_player_columns = (
        required_player_columns
        - player_columns
    )

    for column in sorted(
        required_player_columns
    ):

        if column in player_columns:
            print(
                f"  {column:<20} FOUND"
            )

        else:
            print(
                f"  {column:<20} MISSING"
            )

    if missing_player_columns:

        raise RuntimeError(
            "Missing player columns: "
            + ", ".join(
                sorted(missing_player_columns)
            )
        )

    # ========================================================
    # LOAD PLAYER MASTER
    # ========================================================

    print_section(
        "LOADING PLAYER MASTER"
    )

    player_rows = con.execute(
        """
        SELECT
            reep_id,
            label,
            status,
            gender
        FROM players
        """
    ).fetchall()

    total_players = len(
        player_rows
    )

    print(
        f"Total REEP players: "
        f"{total_players:,}"
    )

    players = {}

    for (
        reep_id,
        label,
        status,
        gender
    ) in player_rows:

        rid = normalize_id(
            reep_id
        )

        if rid is None:
            continue

        players[rid] = {
            "label": label,
            "status": status,
            "gender": gender,
        }

    player_ids = set(
        players.keys()
    )

    # ========================================================
    # GENDER EVIDENCE
    # ========================================================

    print_section(
        "LOADING GENDER EVIDENCE"
    )

    entity_gender_rows = con.execute(
        """
        SELECT
            reep_id,
            gender
        FROM entities
        WHERE reep_id IS NOT NULL
          AND gender IS NOT NULL
        """
    ).fetchall()

    entity_gender = {}

    for reep_id, gender in entity_gender_rows:

        rid = normalize_id(
            reep_id
        )

        if rid in player_ids:

            entity_gender[rid] = gender

    qid_rows = con.execute(
        """
        SELECT DISTINCT
            reep_id
        FROM overlay_links
        WHERE reep_id IS NOT NULL
        """
    ).fetchall()

    qid_players = {
        normalize_id(row[0])
        for row in qid_rows
        if normalize_id(row[0]) in player_ids
    }

    xid_rows = con.execute(
        """
        SELECT DISTINCT
            reep_id
        FROM overlay_xids
        WHERE reep_id IS NOT NULL
        """
    ).fetchall()

    xid_players = {
        normalize_id(row[0])
        for row in xid_rows
        if normalize_id(row[0]) in player_ids
    }

    alias_rows = con.execute(
        """
        SELECT DISTINCT
            reep_id
        FROM aliases
        WHERE reep_id IS NOT NULL
        """
    ).fetchall()

    alias_players = {
        normalize_id(row[0])
        for row in alias_rows
        if normalize_id(row[0]) in player_ids
    }

    overlay_alias_rows = con.execute(
        """
        SELECT DISTINCT
            reep_id
        FROM overlay_aliases
        WHERE reep_id IS NOT NULL
        """
    ).fetchall()

    overlay_alias_players = {
        normalize_id(row[0])
        for row in overlay_alias_rows
        if normalize_id(row[0]) in player_ids
    }

    # ========================================================
    # DOB EVIDENCE
    # ========================================================

    print_section(
        "LOADING DOB EVIDENCE"
    )

    dob_rows = con.execute(
        """
        SELECT DISTINCT
            reep_id
        FROM overlay_links
        WHERE reep_id IS NOT NULL
          AND dob_check IS NOT NULL
          AND LOWER(CAST(dob_check AS VARCHAR))
              NOT IN ('', 'unverified')
        """
    ).fetchall()

    dob_players = {
        normalize_id(row[0])
        for row in dob_rows
        if normalize_id(row[0]) in player_ids
    }

    # ========================================================
    # REDIRECT EVIDENCE
    # ========================================================

    print_section(
        "LOADING REDIRECT EVIDENCE"
    )

    redirect_rows = con.execute(
        """
        SELECT
            from_id,
            to_id
        FROM redirects
        """
    ).fetchall()

    redirect_sources = set()
    redirect_targets = set()

    for from_id, to_id in redirect_rows:

        source = normalize_id(
            from_id
        )

        target = normalize_id(
            to_id
        )

        if source is not None:
            redirect_sources.add(
                source
            )

        if target is not None:
            redirect_targets.add(
                target
            )

    # ========================================================
    # IDENTITY PROFILE
    # ========================================================

    print_section(
        "BUILDING IDENTITY PROFILES"
    )

    profile_counts = {}

    contradiction_counts = {
        "gender_conflict": 0,
        "redirect_status_conflict": 0,
        "redirect_source_and_target": 0,
        "missing_gender_with_identity_evidence": 0,
        "no_identity_evidence": 0,
        "multiple_identity_pathways": 0,
    }

    player_records = []

    for reep_id in player_ids:

        player = players[reep_id]

        label = player["label"]
        status = player["status"]
        gender = player["gender"]

        normalized = normalize_label(
            label
        )

        has_entity_gender = (
            reep_id in entity_gender
        )

        has_qid = (
            reep_id in qid_players
        )

        has_xid = (
            reep_id in xid_players
        )

        has_alias = (
            reep_id in alias_players
        )

        has_overlay_alias = (
            reep_id in overlay_alias_players
        )

        has_dob = (
            reep_id in dob_players
        )

        has_redirect_source = (
            reep_id in redirect_sources
        )

        has_redirect_target = (
            reep_id in redirect_targets
        )

        # ----------------------------------------------------
        # Gender conflict
        # ----------------------------------------------------

        gender_conflict = False

        if (
            gender is not None
            and has_entity_gender
            and str(gender).lower()
            != str(
                entity_gender[reep_id]
            ).lower()
        ):
            gender_conflict = True

        if gender_conflict:
            contradiction_counts[
                "gender_conflict"
            ] += 1

        # ----------------------------------------------------
        # Redirect status conflict
        # ----------------------------------------------------

        redirect_status_conflict = False

        if (
            status == "redirected"
            and not has_redirect_source
        ):
            redirect_status_conflict = True

        elif (
            status != "redirected"
            and has_redirect_source
        ):
            redirect_status_conflict = True

        if redirect_status_conflict:
            contradiction_counts[
                "redirect_status_conflict"
            ] += 1

        # ----------------------------------------------------
        # Both redirect source and target
        # ----------------------------------------------------

        both_redirect_roles = (
            has_redirect_source
            and has_redirect_target
        )

        if both_redirect_roles:

            contradiction_counts[
                "redirect_source_and_target"
            ] += 1

        # ----------------------------------------------------
        # Identity pathways
        # ----------------------------------------------------

        pathways = []

        if gender is not None:
            pathways.append(
                "gender"
            )

        if has_qid:
            pathways.append(
                "qid"
            )

        if has_xid:
            pathways.append(
                "external_id"
            )

        if has_alias:
            pathways.append(
                "alias"
            )

        if has_overlay_alias:
            pathways.append(
                "overlay_alias"
            )

        if has_dob:
            pathways.append(
                "dob"
            )

        if has_redirect_source:
            pathways.append(
                "redirect_source"
            )

        if has_redirect_target:
            pathways.append(
                "redirect_target"
            )

        identity_pathway_count = len(
            pathways
        )

        if identity_pathway_count == 0:

            profile = (
                "no_identity_evidence"
            )

            contradiction_counts[
                "no_identity_evidence"
            ] += 1

        elif (
            gender is None
            and identity_pathway_count > 0
        ):

            profile = (
                "identity_evidence_missing_gender"
            )

            contradiction_counts[
                "missing_gender_with_identity_evidence"
            ] += 1

        elif identity_pathway_count >= 5:

            profile = (
                "strong_multi_pathway_identity"
            )

            contradiction_counts[
                "multiple_identity_pathways"
            ] += 1

        elif identity_pathway_count >= 3:

            profile = (
                "multi_pathway_identity"
            )

            contradiction_counts[
                "multiple_identity_pathways"
            ] += 1

        elif identity_pathway_count == 2:

            profile = (
                "two_pathway_identity"
            )

        else:

            profile = (
                "single_pathway_identity"
            )

        profile_counts[profile] = (
            profile_counts.get(
                profile,
                0
            ) + 1
        )

        # ----------------------------------------------------
        # Overall consistency
        # ----------------------------------------------------

        contradiction_flags = []

        if gender_conflict:
            contradiction_flags.append(
                "gender_conflict"
            )

        if redirect_status_conflict:
            contradiction_flags.append(
                "redirect_status_conflict"
            )

        if both_redirect_roles:
            contradiction_flags.append(
                "redirect_source_and_target"
            )

        has_contradiction = (
            len(contradiction_flags) > 0
        )

        if has_contradiction:
            consistency = (
                "inconsistent"
            )
        else:
            consistency = (
                "consistent"
            )

        player_records.append(
            {
                "reep_id": reep_id,
                "label": label,
                "normalized_label": normalized,
                "status": status,
                "gender": gender,

                "has_entity_gender":
                    yes_no(has_entity_gender),

                "has_qid":
                    yes_no(has_qid),

                "has_external_id":
                    yes_no(has_xid),

                "has_alias":
                    yes_no(has_alias),

                "has_overlay_alias":
                    yes_no(has_overlay_alias),

                "has_dob_evidence":
                    yes_no(has_dob),

                "has_redirect_source":
                    yes_no(has_redirect_source),

                "has_redirect_target":
                    yes_no(has_redirect_target),

                "identity_pathway_count":
                    identity_pathway_count,

                "identity_pathways":
                    "|".join(pathways),

                "gender_conflict":
                    yes_no(gender_conflict),

                "redirect_status_conflict":
                    yes_no(
                        redirect_status_conflict
                    ),

                "both_redirect_roles":
                    yes_no(
                        both_redirect_roles
                    ),

                "consistency":
                    consistency,

                "contradictions":
                    "|".join(
                        contradiction_flags
                    ),

                "profile":
                    profile,
            }
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print_section(
        "IDENTITY CONSISTENCY SUMMARY"
    )

    consistent_count = sum(
        1
        for row in player_records
        if row["consistency"]
        == "consistent"
    )

    inconsistent_count = (
        total_players
        - consistent_count
    )

    consistency_pct = (
        consistent_count
        / total_players
        * 100
        if total_players
        else 0
    )

    print(
        f"Consistent players:       "
        f"{consistent_count:,}"
    )

    print(
        f"Inconsistent players:     "
        f"{inconsistent_count:,}"
    )

    print(
        f"Consistency coverage:     "
        f"{consistency_pct:.2f}%"
    )

    print()

    print(
        f"Gender conflicts:         "
        f"{contradiction_counts['gender_conflict']:,}"
    )

    print(
        f"Redirect/status conflicts:"
        f" {contradiction_counts['redirect_status_conflict']:,}"
    )

    print(
        f"Both redirect roles:      "
        f"{contradiction_counts['redirect_source_and_target']:,}"
    )

    print(
        f"Missing gender + evidence:"
        f" {contradiction_counts['missing_gender_with_identity_evidence']:,}"
    )

    print(
        f"No identity evidence:     "
        f"{contradiction_counts['no_identity_evidence']:,}"
    )

    print(
        f"Multi-pathway identities:  "
        f"{contradiction_counts['multiple_identity_pathways']:,}"
    )

    # ========================================================
    # PROFILE DISTRIBUTION
    # ========================================================

    print_section(
        "IDENTITY PROFILE DISTRIBUTION"
    )

    for profile in sorted(
        profile_counts
    ):

        print(
            f"  {profile:<40}"
            f"{profile_counts[profile]:>10,}"
        )

    # ========================================================
    # EVIDENCE COVERAGE
    # ========================================================

    print_section(
        "IDENTITY EVIDENCE COVERAGE"
    )

    evidence_counts = {
        "gender": sum(
            1
            for row in player_records
            if row["gender"] is not None
        ),

        "qid": len(qid_players),

        "external_id": len(xid_players),

        "alias": len(alias_players),

        "overlay_alias": len(
            overlay_alias_players
        ),

        "dob": len(dob_players),

        "redirect_source": len(
            redirect_sources
            & player_ids
        ),

        "redirect_target": len(
            redirect_targets
            & player_ids
        ),
    }

    for key in [
        "gender",
        "qid",
        "external_id",
        "alias",
        "overlay_alias",
        "dob",
        "redirect_source",
        "redirect_target",
    ]:

        count = evidence_counts[key]

        percentage = (
            count
            / total_players
            * 100
            if total_players
            else 0
        )

        print(
            f"  {key:<25}"
            f"{count:>10,}"
            f"  ({percentage:>6.2f}%)"
        )

    # ========================================================
    # WRITE CSV
    # ========================================================

    print_section(
        "WRITING PLAYER-LEVEL CSV"
    )

    fieldnames = [
        "reep_id",
        "label",
        "normalized_label",
        "status",
        "gender",
        "has_entity_gender",
        "has_qid",
        "has_external_id",
        "has_alias",
        "has_overlay_alias",
        "has_dob_evidence",
        "has_redirect_source",
        "has_redirect_target",
        "identity_pathway_count",
        "identity_pathways",
        "gender_conflict",
        "redirect_status_conflict",
        "both_redirect_roles",
        "consistency",
        "contradictions",
        "profile",
    ]

    with open(
        CSV_PATH,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for row in sorted(
            player_records,
            key=lambda x: (
                x["consistency"],
                str(x["status"]),
                str(x["reep_id"])
            )
        ):

            writer.writerow(row)

    print(
        "CSV saved:"
    )

    print(
        CSV_PATH
    )

    # ========================================================
    # WRITE JSON
    # ========================================================

    print_section(
        "WRITING JSON SUMMARY"
    )

    json_summary = {
        "audit":
            "reep_player_identity_consistency",

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source_database":
            DB_PATH,

        "total_players":
            total_players,

        "consistency": {
            "consistent_players":
                consistent_count,

            "inconsistent_players":
                inconsistent_count,

            "consistency_percentage":
                round(
                    consistency_pct,
                    2
                ),
        },

        "contradictions":
            contradiction_counts,

        "profile_distribution":
            profile_counts,

        "evidence_counts":
            evidence_counts,

        "outputs": {
            "csv":
                CSV_PATH,

            "json":
                JSON_PATH,
        },
    }

    with open(
        JSON_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            json_summary,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(
        "JSON saved:"
    )

    print(
        JSON_PATH
    )

    # ========================================================
    # FINAL
    # ========================================================

    print_section(
        "AUDIT COMPLETE"
    )

    print(
        "Source database was NOT modified."
    )

    print()
    print(
        "Generated files:"
    )

    print(
        f"  {CSV_PATH}"
    )

    print(
        f"  {JSON_PATH}"
    )

    con.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()