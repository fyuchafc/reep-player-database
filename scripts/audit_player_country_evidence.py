from pathlib import Path
import json
import csv
import duckdb
from collections import Counter


# ============================================================
# REEP PLAYER COUNTRY EVIDENCE AUDIT
# ============================================================
#
# READ-ONLY AUDIT
# The source REEP database will NOT be modified.
#
# Purpose:
#   Investigate whether country/nationality evidence exists
#   indirectly through the existing REEP data relationships.
#
# Checks:
#   1. Player master country
#   2. Entity country
#   3. QID / Wikidata relationships
#   4. External-ID relationships
#   5. Alias relationships
#   6. Overlay alias relationships
#   7. Source/provider coverage
#
# Outputs:
#   output/reep-player-country-evidence.csv
#   output/reep-player-country-evidence.json
#
# ============================================================


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

SOURCE_DB = (
    BASE_DIR.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_CSV = OUTPUT_DIR / "reep-player-country-evidence.csv"
OUTPUT_JSON = OUTPUT_DIR / "reep-player-country-evidence.json"


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def safe_str(value):
    if value is None:
        return ""

    return str(value).strip()


def is_present(value):
    if value is None:
        return False

    return str(value).strip() != ""


def table_exists(conn, table_name):
    result = conn.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
        """,
        [table_name],
    ).fetchone()

    return result[0] > 0


def get_columns(conn, table_name):
    rows = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ?
        ORDER BY ordinal_position
        """,
        [table_name],
    ).fetchall()

    return [row[0] for row in rows]


def find_column(columns, candidates):

    lookup = {
        str(column).lower(): column
        for column in columns
    }

    for candidate in candidates:

        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


def print_section(title):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    print("=" * 70)
    print("REEP PLAYER COUNTRY EVIDENCE AUDIT")
    print("=" * 70)

    print()
    print("READ-ONLY — source database will NOT be modified.")

    print()
    print("Database:")
    print(SOURCE_DB)

    if not SOURCE_DB.exists():

        print()
        print("ERROR: Source database was not found.")
        print()
        print("Expected:")
        print(SOURCE_DB)

        return

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # CONNECT
    # --------------------------------------------------------

    print()
    print("Connecting to REEP database...")

    conn = duckdb.connect(
        database=str(SOURCE_DB),
        read_only=True
    )

    print("Connected successfully.")

    # --------------------------------------------------------
    # PLAYERS
    # --------------------------------------------------------

    print_section("CHECKING PLAYERS TABLE")

    if not table_exists(conn, "players"):

        print("ERROR: players table does not exist.")

        conn.close()
        return

    player_columns = get_columns(
        conn,
        "players"
    )

    print("Players table columns:")
    print(", ".join(player_columns))

    player_id_col = find_column(
        player_columns,
        [
            "reep_id",
            "player_id",
            "id"
        ]
    )

    label_col = find_column(
        player_columns,
        [
            "label",
            "name"
        ]
    )

    country_col = find_column(
        player_columns,
        [
            "country",
            "nationality",
            "country_code",
            "nationality_code",
            "birth_country",
            "citizenship"
        ]
    )

    status_col = find_column(
        player_columns,
        [
            "status"
        ]
    )

    gender_col = find_column(
        player_columns,
        [
            "gender",
            "sex"
        ]
    )

    print()
    print("Detected columns:")
    print("  Player ID:", player_id_col)
    print("  Label:", label_col)
    print("  Status:", status_col)
    print("  Gender:", gender_col)
    print("  Country:", country_col)

    if player_id_col is None:

        print()
        print("ERROR: Player ID column could not be detected.")

        conn.close()
        return

    # --------------------------------------------------------
    # LOAD PLAYERS
    # --------------------------------------------------------

    player_query = f"""
        SELECT
            "{player_id_col}" AS reep_id,
            {f'"{label_col}"' if label_col else 'NULL'} AS label,
            {f'"{status_col}"' if status_col else 'NULL'} AS status,
            {f'"{gender_col}"' if gender_col else 'NULL'} AS gender,
            {f'"{country_col}"' if country_col else 'NULL'} AS country
        FROM players
    """

    player_rows = conn.execute(
        player_query
    ).fetchall()

    total_players = len(player_rows)

    print()
    print(
        "Total REEP players:",
        f"{total_players:,}"
    )

    # --------------------------------------------------------
    # PLAYER SET
    # --------------------------------------------------------

    player_ids = {
        row[0]
        for row in player_rows
        if row[0] is not None
    }

    # --------------------------------------------------------
    # MASTER COUNTRY
    # --------------------------------------------------------

    print_section("MASTER COUNTRY EVIDENCE")

    master_country_players = set()

    for row in player_rows:

        reep_id = row[0]
        country = row[4]

        if is_present(country):

            master_country_players.add(
                reep_id
            )

    print(
        "Players with master country:",
        f"{len(master_country_players):,}"
    )

    # --------------------------------------------------------
    # ENTITY COUNTRY
    # --------------------------------------------------------

    print_section("ENTITY COUNTRY EVIDENCE")

    entity_country_players = set()
    entity_country_values = Counter()

    if table_exists(conn, "entities"):

        entity_columns = get_columns(
            conn,
            "entities"
        )

        print("Entities table columns:")
        print(", ".join(entity_columns))

        entity_id_col = find_column(
            entity_columns,
            [
                "reep_id",
                "player_id",
                "id"
            ]
        )

        entity_country_col = find_column(
            entity_columns,
            [
                "country",
                "nationality",
                "country_code",
                "nationality_code",
                "birth_country",
                "citizenship"
            ]
        )

        entity_type_col = find_column(
            entity_columns,
            [
                "entity_type",
                "type"
            ]
        )

        print()
        print(
            "Detected entity ID:",
            entity_id_col
        )

        print(
            "Detected entity country:",
            entity_country_col
        )

        print(
            "Detected entity type:",
            entity_type_col
        )

        if entity_id_col and entity_country_col:

            query = f"""
                SELECT
                    "{entity_id_col}",
                    "{entity_country_col}"
                    {f', "{entity_type_col}"'
                    if entity_type_col else ''}
                FROM entities
            """

            rows = conn.execute(
                query
            ).fetchall()

            for row in rows:

                reep_id = row[0]
                country = row[1]

                if reep_id not in player_ids:
                    continue

                if entity_type_col:

                    entity_type = safe_str(
                        row[2]
                    ).lower()

                    if entity_type != "player":
                        continue

                if is_present(country):

                    entity_country_players.add(
                        reep_id
                    )

                    entity_country_values[
                        safe_str(country)
                    ] += 1

    print()
    print(
        "Players with entity country:",
        f"{len(entity_country_players):,}"
    )

    # --------------------------------------------------------
    # QID EVIDENCE
    # --------------------------------------------------------

    print_section("QID / WIKIDATA EVIDENCE")

    qid_players = set()
    qid_values = Counter()
    qid_confidence = Counter()
    qid_dob_check = Counter()

    overlay_links_rows = 0

    if table_exists(conn, "overlay_links"):

        columns = get_columns(
            conn,
            "overlay_links"
        )

        print("overlay_links columns:")
        print(", ".join(columns))

        id_col = find_column(
            columns,
            [
                "reep_id",
                "player_id",
                "id"
            ]
        )

        qid_col = find_column(
            columns,
            [
                "qid",
                "wikidata_qid"
            ]
        )

        confidence_col = find_column(
            columns,
            [
                "confidence"
            ]
        )

        dob_col = find_column(
            columns,
            [
                "dob_check",
                "date_of_birth_check"
            ]
        )

        entity_type_col = find_column(
            columns,
            [
                "entity_type",
                "type"
            ]
        )

        print()
        print("Detected player ID:", id_col)
        print("Detected QID:", qid_col)
        print("Detected confidence:", confidence_col)
        print("Detected DOB check:", dob_col)
        print("Detected entity type:", entity_type_col)

        if id_col:

            query = f"""
                SELECT
                    "{id_col}"
                    {f', "{qid_col}"'
                    if qid_col else ''}
                    {f', "{confidence_col}"'
                    if confidence_col else ''}
                    {f', "{dob_col}"'
                    if dob_col else ''}
                    {f', "{entity_type_col}"'
                    if entity_type_col else ''}
                FROM overlay_links
            """

            rows = conn.execute(
                query
            ).fetchall()

            overlay_links_rows = len(rows)

            for row in rows:

                index = 0

                reep_id = row[index]
                index += 1

                if reep_id not in player_ids:
                    continue

                if qid_col:

                    qid = row[index]
                    index += 1

                    if is_present(qid):

                        qid_players.add(
                            reep_id
                        )

                        qid_values[
                            safe_str(qid)
                        ] += 1

                if confidence_col:

                    confidence = row[index]
                    index += 1

                    if confidence is not None:

                        qid_confidence[
                            safe_str(confidence)
                        ] += 1

                if dob_col:

                    dob_check = row[index]
                    index += 1

                    if is_present(dob_check):

                        qid_dob_check[
                            safe_str(dob_check)
                        ] += 1

                if entity_type_col:

                    index += 1

    print()
    print(
        "overlay_links rows:",
        f"{overlay_links_rows:,}"
    )

    print(
        "Players with QID:",
        f"{len(qid_players):,}"
    )

    print(
        "Distinct QIDs:",
        f"{len(qid_values):,}"
    )

    # --------------------------------------------------------
    # EXTERNAL ID EVIDENCE
    # --------------------------------------------------------

    print_section("EXTERNAL-ID EVIDENCE")

    xid_players = set()
    provider_counts = Counter()

    xid_rows = 0

    if table_exists(conn, "overlay_xids"):

        columns = get_columns(
            conn,
            "overlay_xids"
        )

        print("overlay_xids columns:")
        print(", ".join(columns))

        xid_id_col = find_column(
            columns,
            [
                "reep_id",
                "player_id",
                "id"
            ]
        )

        provider_col = find_column(
            columns,
            [
                "provider",
                "source"
            ]
        )

        external_id_col = find_column(
            columns,
            [
                "external_id",
                "player_external_id",
                "id_value"
            ]
        )

        qid_col = find_column(
            columns,
            [
                "qid",
                "wikidata_qid"
            ]
        )

        print()
        print(
            "Detected player ID:",
            xid_id_col
        )

        print(
            "Detected provider:",
            provider_col
        )

        print(
            "Detected external ID:",
            external_id_col
        )

        print(
            "Detected QID:",
            qid_col
        )

        if xid_id_col:

            query = f"""
                SELECT
                    "{xid_id_col}"
                    {f', "{provider_col}"'
                    if provider_col else ''}
                    {f', "{external_id_col}"'
                    if external_id_col else ''}
                    {f', "{qid_col}"'
                    if qid_col else ''}
                FROM overlay_xids
            """

            rows = conn.execute(
                query
            ).fetchall()

            xid_rows = len(rows)

            for row in rows:

                reep_id = row[0]

                if reep_id not in player_ids:
                    continue

                xid_players.add(
                    reep_id
                )

                if provider_col and len(row) > 1:

                    provider = safe_str(
                        row[1]
                    )

                    if provider:
                        provider_counts[
                            provider
                        ] += 1

    print()
    print(
        "External-ID rows:",
        f"{xid_rows:,}"
    )

    print(
        "Players with external IDs:",
        f"{len(xid_players):,}"
    )

    print()
    print("Top providers:")

    for provider, count in provider_counts.most_common(20):

        print(
            f"  {provider}: {count:,}"
        )

    # --------------------------------------------------------
    # ALIAS EVIDENCE
    # --------------------------------------------------------

    print_section("ALIAS EVIDENCE")

    alias_players = set()
    alias_rows = 0

    if table_exists(conn, "aliases"):

        columns = get_columns(
            conn,
            "aliases"
        )

        print("aliases columns:")
        print(", ".join(columns))

        alias_id_col = find_column(
            columns,
            [
                "reep_id",
                "player_id",
                "id"
            ]
        )

        if alias_id_col:

            rows = conn.execute(
                f"""
                SELECT "{alias_id_col}"
                FROM aliases
                """
            ).fetchall()

            alias_rows = len(rows)

            for row in rows:

                reep_id = row[0]

                if reep_id in player_ids:

                    alias_players.add(
                        reep_id
                    )

    print()
    print(
        "Alias rows:",
        f"{alias_rows:,}"
    )

    print(
        "Players with aliases:",
        f"{len(alias_players):,}"
    )

    # --------------------------------------------------------
    # OVERLAY ALIAS EVIDENCE
    # --------------------------------------------------------

    print_section("OVERLAY ALIAS EVIDENCE")

    overlay_alias_players = set()
    overlay_alias_rows = 0
    overlay_alias_sources = Counter()

    if table_exists(conn, "overlay_aliases"):

        columns = get_columns(
            conn,
            "overlay_aliases"
        )

        print("overlay_aliases columns:")
        print(", ".join(columns))

        oa_id_col = find_column(
            columns,
            [
                "reep_id",
                "player_id",
                "id"
            ]
        )

        oa_source_col = find_column(
            columns,
            [
                "source",
                "name_source",
                "provider"
            ]
        )

        if oa_id_col:

            query = f"""
                SELECT
                    "{oa_id_col}"
                    {f', "{oa_source_col}"'
                    if oa_source_col else ''}
                FROM overlay_aliases
            """

            rows = conn.execute(
                query
            ).fetchall()

            overlay_alias_rows = len(rows)

            for row in rows:

                reep_id = row[0]

                if reep_id in player_ids:

                    overlay_alias_players.add(
                        reep_id
                    )

                if (
                    oa_source_col
                    and len(row) > 1
                ):

                    source = safe_str(
                        row[1]
                    )

                    if source:

                        overlay_alias_sources[
                            source
                        ] += 1

    print()
    print(
        "Overlay alias rows:",
        f"{overlay_alias_rows:,}"
    )

    print(
        "Players with overlay aliases:",
        f"{len(overlay_alias_players):,}"
    )

    for source, count in overlay_alias_sources.most_common():

        print(
            f"  {source}: {count:,}"
        )

    # --------------------------------------------------------
    # COUNTRY EVIDENCE CLASSIFICATION
    # --------------------------------------------------------

    print_section("COUNTRY EVIDENCE CLASSIFICATION")

    player_records = []

    evidence_counts = Counter()

    for row in player_rows:

        reep_id = row[0]
        label = row[1]
        status = row[2]
        gender = row[3]
        country = row[4]

        has_master_country = (
            reep_id in master_country_players
        )

        has_entity_country = (
            reep_id in entity_country_players
        )

        has_qid = (
            reep_id in qid_players
        )

        has_external_ids = (
            reep_id in xid_players
        )

        has_aliases = (
            reep_id in alias_players
        )

        has_overlay_aliases = (
            reep_id in overlay_alias_players
        )

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # QID, external IDs and aliases are NOT treated as
        # country evidence by themselves.
        #
        # They are recorded as evidence pathways that could
        # potentially support a future enrichment process.
        # ----------------------------------------------------

        if has_master_country and has_entity_country:

            classification = "country_master_and_entity"

        elif has_master_country:

            classification = "country_master_only"

        elif has_entity_country:

            classification = "country_entity_only"

        elif has_qid:

            classification = "qid_pathway"

        elif has_external_ids:

            classification = "external_id_pathway"

        elif has_overlay_aliases:

            classification = "alias_pathway"

        elif has_aliases:

            classification = "alias_only"

        else:

            classification = "no_country_pathway"

        evidence_counts[
            classification
        ] += 1

        player_records.append(
            {
                "reep_id": safe_str(reep_id),
                "label": safe_str(label),
                "status": safe_str(status),
                "gender": safe_str(gender),
                "master_country": safe_str(country),
                "has_master_country": has_master_country,
                "has_entity_country": has_entity_country,
                "has_qid": has_qid,
                "has_external_ids": has_external_ids,
                "has_aliases": has_aliases,
                "has_overlay_aliases": has_overlay_aliases,
                "country_evidence_classification": classification,
            }
        )

    print()

    for classification, count in evidence_counts.most_common():

        print(
            f"  {classification}: {count:,}"
        )

    # --------------------------------------------------------
    # IMPORTANT COVERAGE OVERLAPS
    # --------------------------------------------------------

    print_section("EVIDENCE PATHWAY COVERAGE")

    print(
        "Players with QID:",
        f"{len(qid_players):,}"
    )

    print(
        "Players with external IDs:",
        f"{len(xid_players):,}"
    )

    print(
        "Players with aliases:",
        f"{len(alias_players):,}"
    )

    print(
        "Players with overlay aliases:",
        f"{len(overlay_alias_players):,}"
    )

    print(
        "Players with any indirect pathway:",
        f"{len(
            qid_players
            | xid_players
            | alias_players
            | overlay_alias_players
        ):,}"
    )

    print(
        "Players with no country pathway:",
        f"{len(
            player_ids
            - (
                qid_players
                | xid_players
                | alias_players
                | overlay_alias_players
            )
        ):,}"
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = {

        "audit":
            "REEP Player Country Evidence Audit",

        "read_only":
            True,

        "database":
            str(SOURCE_DB),

        "total_players":
            total_players,

        "master_country_players":
            len(master_country_players),

        "entity_country_players":
            len(entity_country_players),

        "qid_players":
            len(qid_players),

        "distinct_qids":
            len(qid_values),

        "external_id_rows":
            xid_rows,

        "external_id_players":
            len(xid_players),

        "alias_rows":
            alias_rows,

        "alias_players":
            len(alias_players),

        "overlay_alias_rows":
            overlay_alias_rows,

        "overlay_alias_players":
            len(overlay_alias_players),

        "players_with_any_indirect_pathway":
            len(
                qid_players
                | xid_players
                | alias_players
                | overlay_alias_players
            ),

        "players_with_no_country_pathway":
            len(
                player_ids
                - (
                    qid_players
                    | xid_players
                    | alias_players
                    | overlay_alias_players
                )
            ),

        "evidence_classification":
            dict(evidence_counts),

        "top_entity_country_values":
            [
                {
                    "country": country,
                    "count": count
                }
                for country, count
                in entity_country_values.most_common(50)
            ],

        "provider_counts":
            dict(
                provider_counts.most_common()
            ),

        "overlay_alias_sources":
            dict(
                overlay_alias_sources.most_common()
            ),

        "qid_confidence_counts":
            dict(qid_confidence),

        "qid_dob_check_counts":
            dict(qid_dob_check),
    }

    # --------------------------------------------------------
    # WRITE CSV
    # --------------------------------------------------------

    print_section("WRITING OUTPUT FILES")

    fieldnames = [
        "reep_id",
        "label",
        "status",
        "gender",
        "master_country",
        "has_master_country",
        "has_entity_country",
        "has_qid",
        "has_external_ids",
        "has_aliases",
        "has_overlay_aliases",
        "country_evidence_classification",
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
        writer.writerows(
            player_records
        )

    # --------------------------------------------------------
    # WRITE JSON
    # --------------------------------------------------------

    output_data = {
        "summary": summary,
        "players": player_records,
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output_data,
            f,
            indent=2,
            ensure_ascii=False
        )

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print()
    print("CSV:")
    print(OUTPUT_CSV)

    print()
    print("JSON:")
    print(OUTPUT_JSON)

    print()
    print("=" * 70)
    print("COUNTRY EVIDENCE AUDIT COMPLETE")
    print("=" * 70)

    conn.close()


# ------------------------------------------------------------
# RUN
# ------------------------------------------------------------

if __name__ == "__main__":
    main()