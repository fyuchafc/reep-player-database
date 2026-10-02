from pathlib import Path
import json
import csv
import duckdb
from collections import Counter


# ============================================================
# REEP PLAYER COUNTRY SOURCES AUDIT
# ============================================================
#
# READ-ONLY AUDIT
# The source REEP database will NOT be modified.
#
# Purpose:
#   Audit where player country information exists, where it is
#   missing, and which REEP source tables can potentially
#   provide country/nationality information.
#
# Outputs:
#   output/reep-player-country-sources.csv
#   output/reep-player-country-sources.json
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

OUTPUT_CSV = OUTPUT_DIR / "reep-player-country-sources.csv"
OUTPUT_JSON = OUTPUT_DIR / "reep-player-country-sources.json"


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

    value = str(value).strip()

    if value == "":
        return False

    return True


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
    """
    Find the first matching column from a list of candidates.
    Matching is case-insensitive.
    """

    lookup = {str(col).lower(): col for col in columns}

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
# MAIN AUDIT
# ------------------------------------------------------------

def main():

    print("=" * 70)
    print("REEP PLAYER COUNTRY SOURCES AUDIT")
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
        print("Expected path:")
        print(SOURCE_DB)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # CONNECT READ-ONLY
    # --------------------------------------------------------

    print()
    print("Connecting to REEP database...")

    conn = duckdb.connect(
        database=str(SOURCE_DB),
        read_only=True
    )

    print("Connected successfully.")

    # --------------------------------------------------------
    # CHECK PLAYERS TABLE
    # --------------------------------------------------------

    print_section("CHECKING PLAYERS TABLE")

    if not table_exists(conn, "players"):
        print("ERROR: players table does not exist.")
        conn.close()
        return

    player_columns = get_columns(conn, "players")

    print("Players table columns:")
    print(", ".join(player_columns))

    player_id_col = find_column(
        player_columns,
        ["reep_id", "player_id", "id"]
    )

    country_col = find_column(
        player_columns,
        [
            "country",
            "nationality",
            "country_code",
            "nationality_code",
            "birth_country",
            "citizenship",
        ]
    )

    label_col = find_column(
        player_columns,
        ["label", "name"]
    )

    status_col = find_column(
        player_columns,
        ["status"]
    )

    gender_col = find_column(
        player_columns,
        ["gender", "sex"]
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
        print("ERROR: Could not identify player ID column.")
        conn.close()
        return

    # --------------------------------------------------------
    # LOAD PLAYER MASTER
    # --------------------------------------------------------

    player_query = f"""
        SELECT
            "{player_id_col}" AS reep_id
            {f', "{label_col}" AS label' if label_col else ', NULL AS label'}
            {f', "{status_col}" AS status' if status_col else ', NULL AS status'}
            {f', "{gender_col}" AS gender' if gender_col else ', NULL AS gender'}
            {f', "{country_col}" AS country' if country_col else ', NULL AS country'}
        FROM players
    """

    player_rows = conn.execute(player_query).fetchall()

    total_players = len(player_rows)

    print()
    print("Total REEP players:", f"{total_players:,}")

    # --------------------------------------------------------
    # MASTER COUNTRY COMPLETENESS
    # --------------------------------------------------------

    print_section("PLAYER MASTER COUNTRY COMPLETENESS")

    country_present = 0
    country_missing = 0

    status_counts = Counter()
    gender_counts = Counter()
    country_values = Counter()

    for row in player_rows:

        reep_id = row[0]
        label = row[1]
        status = row[2]
        gender = row[3]
        country = row[4]

        if is_present(country):
            country_present += 1
            country_values[safe_str(country)] += 1
        else:
            country_missing += 1

        status_counts[safe_str(status) or "NULL"] += 1
        gender_counts[safe_str(gender) or "NULL"] += 1

    country_coverage = (
        country_present / total_players * 100
        if total_players
        else 0
    )

    print("Country present:", f"{country_present:,}")
    print("Country missing:", f"{country_missing:,}")
    print("Country coverage:", f"{country_coverage:.2f}%")

    print()
    print("Status:")
    for key, value in status_counts.most_common():
        print(f"  {key}: {value:,}")

    print()
    print("Gender:")
    for key, value in gender_counts.most_common():
        print(f"  {key}: {value:,}")

    # --------------------------------------------------------
    # ENTITY COUNTRY SOURCE
    # --------------------------------------------------------

    print_section("ENTITY COUNTRY SOURCE")

    entity_country_rows = 0
    entity_country_players = set()
    entity_country_values = Counter()

    if table_exists(conn, "entities"):

        entity_columns = get_columns(conn, "entities")

        print("Entities table columns:")
        print(", ".join(entity_columns))

        entity_id_col = find_column(
            entity_columns,
            ["reep_id", "player_id", "id"]
        )

        entity_country_col = find_column(
            entity_columns,
            [
                "country",
                "nationality",
                "country_code",
                "nationality_code",
                "birth_country",
                "citizenship",
            ]
        )

        entity_type_col = find_column(
            entity_columns,
            ["entity_type", "type"]
        )

        print()
        print("Detected entity ID column:", entity_id_col)
        print("Detected country column:", entity_country_col)
        print("Detected entity type column:", entity_type_col)

        if entity_id_col and entity_country_col:

            entity_query = f"""
                SELECT
                    "{entity_id_col}",
                    "{entity_country_col}"
                    {f', "{entity_type_col}"' if entity_type_col else ''}
                FROM entities
            """

            entity_rows = conn.execute(entity_query).fetchall()

            for row in entity_rows:

                reep_id = row[0]
                country = row[1]

                if not is_present(country):
                    continue

                if entity_type_col:
                    entity_type = row[2]

                    if safe_str(entity_type).lower() != "player":
                        continue

                entity_country_rows += 1
                entity_country_players.add(reep_id)
                entity_country_values[safe_str(country)] += 1

    else:
        print("Entities table not found.")

    print()
    print("Entity country rows:", f"{entity_country_rows:,}")
    print("Players with entity country:", f"{len(entity_country_players):,}")

    # --------------------------------------------------------
    # OVERLAY ALIAS COUNTRY / NATIONALITY SOURCES
    # --------------------------------------------------------

    print_section("OVERLAY SOURCES")

    overlay_links_rows = 0
    overlay_links_dob_rows = 0

    if table_exists(conn, "overlay_links"):

        columns = get_columns(conn, "overlay_links")

        print("overlay_links columns:")
        print(", ".join(columns))

        overlay_id_col = find_column(
            columns,
            ["reep_id", "player_id", "id"]
        )

        dob_col = find_column(
            columns,
            ["dob_check", "date_of_birth_check"]
        )

        print()
        print("Detected player ID:", overlay_id_col)
        print("Detected DOB check:", dob_col)

        overlay_links_rows = conn.execute(
            "SELECT COUNT(*) FROM overlay_links"
        ).fetchone()[0]

        if dob_col:
            overlay_links_dob_rows = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM overlay_links
                WHERE "{dob_col}" IS NOT NULL
                """
            ).fetchone()[0]

    print()
    print("overlay_links rows:", f"{overlay_links_rows:,}")

    if overlay_links_dob_rows:
        print(
            "overlay_links rows with DOB evidence:",
            f"{overlay_links_dob_rows:,}"
        )

    # --------------------------------------------------------
    # OVERLAY XIDS
    # --------------------------------------------------------

    print_section("EXTERNAL ID SOURCES")

    xid_rows = 0
    xid_players = set()
    provider_counts = Counter()

    if table_exists(conn, "overlay_xids"):

        columns = get_columns(conn, "overlay_xids")

        print("overlay_xids columns:")
        print(", ".join(columns))

        xid_id_col = find_column(
            columns,
            ["reep_id", "player_id", "id"]
        )

        provider_col = find_column(
            columns,
            ["provider", "source"]
        )

        external_id_col = find_column(
            columns,
            ["external_id", "player_external_id", "id_value"]
        )

        print()
        print("Detected player ID:", xid_id_col)
        print("Detected provider:", provider_col)
        print("Detected external ID:", external_id_col)

        if xid_id_col:

            xid_query = f"""
                SELECT
                    "{xid_id_col}"
                    {f', "{provider_col}"' if provider_col else ''}
                FROM overlay_xids
            """

            xid_data = conn.execute(xid_query).fetchall()

            xid_rows = len(xid_data)

            for row in xid_data:

                reep_id = row[0]

                if reep_id is not None:
                    xid_players.add(reep_id)

                if provider_col and len(row) > 1:
                    provider = safe_str(row[1])

                    if provider:
                        provider_counts[provider] += 1

    print()
    print("External ID rows:", f"{xid_rows:,}")
    print("Players with external IDs:", f"{len(xid_players):,}")

    if provider_counts:

        print()
        print("Top external-ID providers:")

        for provider, count in provider_counts.most_common(20):
            print(f"  {provider}: {count:,}")

    # --------------------------------------------------------
    # ALIASES
    # --------------------------------------------------------

    print_section("ALIAS SOURCES")

    alias_rows = 0
    alias_players = set()

    if table_exists(conn, "aliases"):

        columns = get_columns(conn, "aliases")

        print("aliases columns:")
        print(", ".join(columns))

        alias_id_col = find_column(
            columns,
            ["reep_id", "player_id", "id"]
        )

        if alias_id_col:

            alias_data = conn.execute(
                f"""
                SELECT "{alias_id_col}"
                FROM aliases
                """
            ).fetchall()

            alias_rows = len(alias_data)

            for row in alias_data:
                if row[0] is not None:
                    alias_players.add(row[0])

    print()
    print("Alias rows:", f"{alias_rows:,}")
    print("Players with aliases:", f"{len(alias_players):,}")

    # --------------------------------------------------------
    # OVERLAY ALIASES
    # --------------------------------------------------------

    print_section("OVERLAY ALIAS SOURCES")

    overlay_alias_rows = 0
    overlay_alias_players = set()
    overlay_alias_source_counts = Counter()

    if table_exists(conn, "overlay_aliases"):

        columns = get_columns(conn, "overlay_aliases")

        print("overlay_aliases columns:")
        print(", ".join(columns))

        oa_id_col = find_column(
            columns,
            ["reep_id", "player_id", "id"]
        )

        oa_source_col = find_column(
            columns,
            ["source", "name_source", "provider"]
        )

        if oa_id_col:

            query = f"""
                SELECT
                    "{oa_id_col}"
                    {f', "{oa_source_col}"' if oa_source_col else ''}
                FROM overlay_aliases
            """

            rows = conn.execute(query).fetchall()

            overlay_alias_rows = len(rows)

            for row in rows:

                reep_id = row[0]

                if reep_id is not None:
                    overlay_alias_players.add(reep_id)

                if oa_source_col and len(row) > 1:
                    source = safe_str(row[1])

                    if source:
                        overlay_alias_source_counts[source] += 1

    print()
    print("Overlay alias rows:", f"{overlay_alias_rows:,}")
    print(
        "Players with overlay aliases:",
        f"{len(overlay_alias_players):,}"
    )

    if overlay_alias_source_counts:

        print()
        print("Overlay alias sources:")

        for source, count in overlay_alias_source_counts.most_common():
            print(f"  {source}: {count:,}")

    # --------------------------------------------------------
    # COUNTRY SOURCE OVERLAP
    # --------------------------------------------------------

    print_section("COUNTRY SOURCE COVERAGE")

    master_country_players = set()

    for row in player_rows:
        if is_present(row[4]):
            master_country_players.add(row[0])

    entity_only_country = (
        entity_country_players - master_country_players
    )

    master_and_entity_country = (
        master_country_players & entity_country_players
    )

    print(
        "Players with country in master:",
        f"{len(master_country_players):,}"
    )

    print(
        "Players with country in entity:",
        f"{len(entity_country_players):,}"
    )

    print(
        "Country present in both master + entity:",
        f"{len(master_and_entity_country):,}"
    )

    print(
        "Entity country not in master:",
        f"{len(entity_only_country):,}"
    )

    # --------------------------------------------------------
    # PLAYER-LEVEL SOURCE REPORT
    # --------------------------------------------------------

    print_section("BUILDING PLAYER-LEVEL COUNTRY SOURCE REPORT")

    player_records = []

    for row in player_rows:

        reep_id = row[0]
        label = row[1]
        status = row[2]
        gender = row[3]
        country = row[4]

        master_has_country = is_present(country)
        entity_has_country = reep_id in entity_country_players
        has_alias = reep_id in alias_players
        has_overlay_alias = reep_id in overlay_alias_players
        has_external_ids = reep_id in xid_players

        source_count = sum(
            [
                master_has_country,
                entity_has_country,
            ]
        )

        if master_has_country and entity_has_country:
            country_source_status = "master_and_entity"

        elif master_has_country:
            country_source_status = "master_only"

        elif entity_has_country:
            country_source_status = "entity_only"

        else:
            country_source_status = "no_country"

        player_records.append(
            {
                "reep_id": safe_str(reep_id),
                "label": safe_str(label),
                "status": safe_str(status),
                "gender": safe_str(gender),
                "master_country": safe_str(country),
                "master_has_country": master_has_country,
                "entity_has_country": entity_has_country,
                "has_alias": has_alias,
                "has_overlay_alias": has_overlay_alias,
                "has_external_ids": has_external_ids,
                "country_source_count": source_count,
                "country_source_status": country_source_status,
            }
        )

    # --------------------------------------------------------
    # SOURCE STATUS COUNTS
    # --------------------------------------------------------

    source_status_counts = Counter(
        record["country_source_status"]
        for record in player_records
    )

    print()
    print("Country source status:")

    for key, count in source_status_counts.most_common():
        print(f"  {key}: {count:,}")

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = {
        "audit": "REEP Player Country Sources Audit",
        "read_only": True,
        "database": str(SOURCE_DB),
        "total_players": total_players,
        "players_country_present": country_present,
        "players_country_missing": country_missing,
        "country_coverage_percent": round(country_coverage, 2),
        "players_entity_country": len(entity_country_players),
        "entity_country_rows": entity_country_rows,
        "master_and_entity_country": len(master_and_entity_country),
        "entity_country_not_in_master": len(entity_only_country),
        "overlay_links_rows": overlay_links_rows,
        "overlay_links_dob_evidence_rows": overlay_links_dob_rows,
        "external_id_rows": xid_rows,
        "players_with_external_ids": len(xid_players),
        "alias_rows": alias_rows,
        "players_with_aliases": len(alias_players),
        "overlay_alias_rows": overlay_alias_rows,
        "players_with_overlay_aliases": len(overlay_alias_players),
        "country_source_status": dict(source_status_counts),
        "top_master_country_values": [
            {
                "country": country,
                "count": count,
            }
            for country, count in country_values.most_common(50)
        ],
        "top_entity_country_values": [
            {
                "country": country,
                "count": count,
            }
            for country, count in entity_country_values.most_common(50)
        ],
        "external_id_provider_counts": dict(
            provider_counts.most_common()
        ),
        "overlay_alias_source_counts": dict(
            overlay_alias_source_counts.most_common()
        ),
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
        "master_has_country",
        "entity_has_country",
        "has_alias",
        "has_overlay_alias",
        "has_external_ids",
        "country_source_count",
        "country_source_status",
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(player_records)

    # --------------------------------------------------------
    # WRITE JSON
    # --------------------------------------------------------

    json_output = {
        "summary": summary,
        "players": player_records,
    }

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            json_output,
            f,
            indent=2,
            ensure_ascii=False,
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
    print("COUNTRY SOURCES AUDIT COMPLETE")
    print("=" * 70)

    conn.close()


# ------------------------------------------------------------
# RUN
# ------------------------------------------------------------

if __name__ == "__main__":
    main()