import duckdb
from pathlib import Path

# ================================================================
# REEP V1.2 — FINAL MASTER DATABASE AUDIT
# ================================================================
#
# READ-ONLY AUDIT
#
# Database:
#   output/reep-player-master-v1.2.duckdb
#
# This script does NOT modify the database.
#
# It checks:
#   1. Required tables
#   2. Required columns
#   3. Player identity integrity
#   4. Alias integrity
#   5. External-ID integrity
#   6. Redirect integrity
#   7. Club-evidence integrity
#   8. Position integrity
#   9. Position-claim integrity
#  10. Search-index integrity
#  11. Metadata integrity
#  12. Expected production counts
#
# ================================================================


DATABASE = Path(
    r"output\reep-player-master-v1.2.duckdb"
)

EXPECTED_COUNTS = {
    "players": 432_124,
    "player_aliases": 1_053_507,
    "player_external_ids": 3_659_608,
    "player_redirects": 1_195,
    "player_club_evidence": 142_518,
    "player_position": 5_500,
    "player_position_claims": 8_385,
    "player_search": 432_124,
    "database_metadata": 14,
}


REQUIRED_TABLES = {
    "players": [
        "reep_id",
        "status",
        "label",
        "gender",
        "country",
    ],

    "player_aliases": [
        "reep_id",
        "alias",
        "alias_kind",
        "language",
        "source",
        "confidence",
        "rank",
    ],

    "player_external_ids": [
        "reep_id",
        "provider",
        "namespace",
        "external_id",
        "property",
        "rank",
        "confidence",
        "source",
    ],

    "player_redirects": [
        "from_id",
        "to_id",
        "reason",
    ],

    "player_club_evidence": [
        "reep_id",
        "entity_type",
        "observed_clubs",
        "first_observed_season",
        "last_observed_season",
        "basis",
    ],

    "player_position": [
        "reep_id",
        "label",
        "primary_position",
        "secondary_positions",
        "position_status",
        "evidence_count",
        "provider_count",
        "source",
        "updated_at",
    ],

    "player_position_claims": [
        "reep_id",
        "label",
        "provider",
        "provider_namespace",
        "provider_id",
        "position",
        "position_normalized",
        "position_type",
        "source_url",
        "http_status",
        "parser_version",
        "retrieved_at",
    ],

    "player_search": [
        "reep_id",
        "label",
        "search_text",
        "alias_count",
        "external_id_count",
    ],

    "database_metadata": [
        "key",
        "value",
    ],
}


# ================================================================
# HELPERS
# ================================================================

PASS_COUNT = 0
FAIL_COUNT = 0
WARN_COUNT = 0


def section(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def check(name, condition, detail=""):

    global PASS_COUNT
    global FAIL_COUNT

    if condition:

        PASS_COUNT += 1

        print(
            f"PASS  {name}"
            + (f" — {detail}" if detail else "")
        )

    else:

        FAIL_COUNT += 1

        print(
            f"FAIL  {name}"
            + (f" — {detail}" if detail else "")
        )


def warning(name, detail=""):

    global WARN_COUNT

    WARN_COUNT += 1

    print(
        f"WARN  {name}"
        + (f" — {detail}" if detail else "")
    )


def count(con, table):

    return con.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]


def null_or_empty_count(con, table, column):

    return con.execute(
        f"""
        SELECT COUNT(*)
        FROM "{table}"
        WHERE
            "{column}" IS NULL
            OR TRIM(CAST("{column}" AS VARCHAR)) = ''
        """
    ).fetchone()[0]


# ================================================================
# START
# ================================================================

section("REEP V1.2 — FINAL MASTER DATABASE AUDIT")

print()
print("Database:")
print(DATABASE)

print()
print("MODE: READ-ONLY")

if not DATABASE.exists():

    print()
    print("ERROR: Database does not exist.")
    print(DATABASE)
    raise SystemExit(1)


con = duckdb.connect(
    str(DATABASE),
    read_only=True
)

print()
print("Database opened successfully.")


# ================================================================
# 1. REQUIRED TABLES
# ================================================================

section("1. REQUIRED TABLES")

existing_tables = {
    row[0]
    for row in con.execute(
        "SHOW TABLES"
    ).fetchall()
}

for table in REQUIRED_TABLES:

    check(
        f"Table exists: {table}",
        table in existing_tables
    )


# ================================================================
# 2. REQUIRED COLUMNS
# ================================================================

section("2. REQUIRED COLUMNS")

for table, required_columns in REQUIRED_TABLES.items():

    if table not in existing_tables:
        continue

    actual_columns = {
        row[0]
        for row in con.execute(
            f'DESCRIBE "{table}"'
        ).fetchall()
    }

    missing = [
        column
        for column in required_columns
        if column not in actual_columns
    ]

    check(
        f"Columns: {table}",
        len(missing) == 0,
        "all required columns present"
        if not missing
        else f"missing: {missing}"
    )


# ================================================================
# 3. TABLE COUNTS
# ================================================================

section("3. TABLE COUNTS")

actual_counts = {}

for table, expected in EXPECTED_COUNTS.items():

    if table not in existing_tables:
        continue

    actual = count(
        con,
        table
    )

    actual_counts[table] = actual

    check(
        f"Count: {table}",
        actual == expected,
        f"{actual:,} / expected {expected:,}"
    )


# ================================================================
# 4. PLAYER IDENTITY INTEGRITY
# ================================================================

section("4. PLAYER IDENTITY INTEGRITY")

players = actual_counts.get(
    "players",
    0
)

duplicate_players = con.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT reep_id
        FROM players
        GROUP BY reep_id
        HAVING COUNT(*) > 1
    )
""").fetchone()[0]

check(
    "Duplicate player REEP IDs",
    duplicate_players == 0,
    f"{duplicate_players:,}"
)


null_player_ids = null_or_empty_count(
    con,
    "players",
    "reep_id"
)

check(
    "Null/empty player REEP IDs",
    null_player_ids == 0,
    f"{null_player_ids:,}"
)


distinct_players = con.execute("""
    SELECT COUNT(DISTINCT reep_id)
    FROM players
""").fetchone()[0]

check(
    "Distinct player IDs equal player count",
    distinct_players == players,
    f"{distinct_players:,}"
)


# ================================================================
# 5. PLAYER ALIAS INTEGRITY
# ================================================================

section("5. PLAYER ALIAS INTEGRITY")

alias_orphans = con.execute("""
    SELECT COUNT(*)
    FROM player_aliases a
    LEFT JOIN players p
        ON a.reep_id = p.reep_id
    WHERE p.reep_id IS NULL
""").fetchone()[0]

check(
    "Alias orphan records",
    alias_orphans == 0,
    f"{alias_orphans:,}"
)


alias_null_ids = null_or_empty_count(
    con,
    "player_aliases",
    "reep_id"
)

check(
    "Alias null/empty REEP IDs",
    alias_null_ids == 0,
    f"{alias_null_ids:,}"
)


alias_null_names = null_or_empty_count(
    con,
    "player_aliases",
    "alias"
)

check(
    "Alias null/empty names",
    alias_null_names == 0,
    f"{alias_null_names:,}"
)


# ================================================================
# 6. EXTERNAL-ID INTEGRITY
# ================================================================

section("6. EXTERNAL-ID INTEGRITY")

external_orphans = con.execute("""
    SELECT COUNT(*)
    FROM player_external_ids e
    LEFT JOIN players p
        ON e.reep_id = p.reep_id
    WHERE p.reep_id IS NULL
""").fetchone()[0]

check(
    "External-ID orphan records",
    external_orphans == 0,
    f"{external_orphans:,}"
)


external_null_ids = null_or_empty_count(
    con,
    "player_external_ids",
    "reep_id"
)

check(
    "External-ID null/empty REEP IDs",
    external_null_ids == 0,
    f"{external_null_ids:,}"
)


external_null_external_ids = null_or_empty_count(
    con,
    "player_external_ids",
    "external_id"
)

check(
    "Null/empty external IDs",
    external_null_external_ids == 0,
    f"{external_null_external_ids:,}"
)


external_null_provider = null_or_empty_count(
    con,
    "player_external_ids",
    "provider"
)

check(
    "Null/empty external-ID providers",
    external_null_provider == 0,
    f"{external_null_provider:,}"
)


# ================================================================
# 7. REDIRECT INTEGRITY
# ================================================================

section("7. REDIRECT INTEGRITY")

redirect_null_from = null_or_empty_count(
    con,
    "player_redirects",
    "from_id"
)

check(
    "Redirect null/empty from_id",
    redirect_null_from == 0,
    f"{redirect_null_from:,}"
)


redirect_null_to = null_or_empty_count(
    con,
    "player_redirects",
    "to_id"
)

check(
    "Redirect null/empty to_id",
    redirect_null_to == 0,
    f"{redirect_null_to:,}"
)


redirects_invalid = con.execute("""
    SELECT COUNT(*)
    FROM player_redirects r
    WHERE
        NOT EXISTS (
            SELECT 1
            FROM players p
            WHERE p.reep_id = r.from_id
        )
        AND NOT EXISTS (
            SELECT 1
            FROM players p
            WHERE p.reep_id = r.to_id
        )
""").fetchone()[0]

check(
    "Redirects unrelated to player identities",
    redirects_invalid == 0,
    f"{redirects_invalid:,}"
)


# ================================================================
# 8. CLUB EVIDENCE INTEGRITY
# ================================================================

section("8. PLAYER CLUB EVIDENCE INTEGRITY")

club_orphans = con.execute("""
    SELECT COUNT(*)
    FROM player_club_evidence c
    LEFT JOIN players p
        ON c.reep_id = p.reep_id
    WHERE p.reep_id IS NULL
""").fetchone()[0]

check(
    "Club evidence orphan records",
    club_orphans == 0,
    f"{club_orphans:,}"
)


club_non_player = con.execute("""
    SELECT COUNT(*)
    FROM player_club_evidence
    WHERE
        LOWER(TRIM(entity_type)) <> 'player'
        OR entity_type IS NULL
""").fetchone()[0]

check(
    "Club evidence non-player entity types",
    club_non_player == 0,
    f"{club_non_player:,}"
)


club_null_ids = null_or_empty_count(
    con,
    "player_club_evidence",
    "reep_id"
)

check(
    "Club evidence null/empty REEP IDs",
    club_null_ids == 0,
    f"{club_null_ids:,}"
)


# ================================================================
# 9. POSITION MASTER INTEGRITY
# ================================================================

section("9. PLAYER POSITION INTEGRITY")

position_orphans = con.execute("""
    SELECT COUNT(*)
    FROM player_position pp
    LEFT JOIN players p
        ON pp.reep_id = p.reep_id
    WHERE p.reep_id IS NULL
""").fetchone()[0]

check(
    "Position orphan records",
    position_orphans == 0,
    f"{position_orphans:,}"
)


position_null_ids = null_or_empty_count(
    con,
    "player_position",
    "reep_id"
)

check(
    "Position null/empty REEP IDs",
    position_null_ids == 0,
    f"{position_null_ids:,}"
)


position_duplicate_ids = con.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT reep_id
        FROM player_position
        GROUP BY reep_id
        HAVING COUNT(*) > 1
    )
""").fetchone()[0]

check(
    "Duplicate position REEP IDs",
    position_duplicate_ids == 0,
    f"{position_duplicate_ids:,}"
)


position_invalid_status = con.execute("""
    SELECT COUNT(*)
    FROM player_position
    WHERE position_status NOT IN (
        'supported',
        'no_position'
    )
""").fetchone()[0]

check(
    "Invalid position status values",
    position_invalid_status == 0,
    f"{position_invalid_status:,}"
)


position_negative_evidence = con.execute("""
    SELECT COUNT(*)
    FROM player_position
    WHERE evidence_count < 0
""").fetchone()[0]

check(
    "Negative position evidence counts",
    position_negative_evidence == 0,
    f"{position_negative_evidence:,}"
)


position_negative_providers = con.execute("""
    SELECT COUNT(*)
    FROM player_position
    WHERE provider_count < 0
""").fetchone()[0]

check(
    "Negative position provider counts",
    position_negative_providers == 0,
    f"{position_negative_providers:,}"
)


# ================================================================
# 10. POSITION CLAIM INTEGRITY
# ================================================================

section("10. PLAYER POSITION CLAIM INTEGRITY")

claim_orphans = con.execute("""
    SELECT COUNT(*)
    FROM player_position_claims c
    LEFT JOIN players p
        ON c.reep_id = p.reep_id
    WHERE p.reep_id IS NULL
""").fetchone()[0]

check(
    "Position claim orphan records",
    claim_orphans == 0,
    f"{claim_orphans:,}"
)


claim_null_ids = null_or_empty_count(
    con,
    "player_position_claims",
    "reep_id"
)

check(
    "Position claim null/empty REEP IDs",
    claim_null_ids == 0,
    f"{claim_null_ids:,}"
)


claim_empty_position = null_or_empty_count(
    con,
    "player_position_claims",
    "position_normalized"
)

check(
    "Empty normalized positions",
    claim_empty_position == 0,
    f"{claim_empty_position:,}"
)


claim_invalid_types = con.execute("""
    SELECT COUNT(*)
    FROM player_position_claims
    WHERE position_type NOT IN (
        'main',
        'other'
    )
""").fetchone()[0]

check(
    "Invalid position claim types",
    claim_invalid_types == 0,
    f"{claim_invalid_types:,}"
)


claim_invalid_http = con.execute("""
    SELECT COUNT(*)
    FROM player_position_claims
    WHERE
        http_status IS NOT NULL
        AND (
            http_status < 100
            OR http_status > 599
        )
""").fetchone()[0]

check(
    "Invalid HTTP status codes",
    claim_invalid_http == 0,
    f"{claim_invalid_http:,}"
)


# ================================================================
# 11. POSITION EVIDENCE COUNT INTEGRITY
# ================================================================

section("11. POSITION EVIDENCE COUNT INTEGRITY")

evidence_mismatches = con.execute("""
    SELECT COUNT(*)
    FROM player_position pp

    LEFT JOIN (
        SELECT
            reep_id,
            COUNT(*) AS claim_count,
            COUNT(DISTINCT provider) AS provider_count
        FROM player_position_claims
        GROUP BY reep_id
    ) c
        ON pp.reep_id = c.reep_id

    WHERE
        pp.evidence_count
            <> COALESCE(c.claim_count, 0)

        OR

        pp.provider_count
            <> COALESCE(c.provider_count, 0)
""").fetchone()[0]

check(
    "Position evidence/provider counts match claims",
    evidence_mismatches == 0,
    f"{evidence_mismatches:,}"
)


# ================================================================
# 12. SEARCH INDEX INTEGRITY
# ================================================================

section("12. PLAYER SEARCH INDEX INTEGRITY")

search_orphans = con.execute("""
    SELECT COUNT(*)
    FROM player_search s
    LEFT JOIN players p
        ON s.reep_id = p.reep_id
    WHERE p.reep_id IS NULL
""").fetchone()[0]

check(
    "Search-index orphan records",
    search_orphans == 0,
    f"{search_orphans:,}"
)


search_missing = con.execute("""
    SELECT COUNT(*)
    FROM players p
    LEFT JOIN player_search s
        ON p.reep_id = s.reep_id
    WHERE s.reep_id IS NULL
""").fetchone()[0]

check(
    "Players missing from search index",
    search_missing == 0,
    f"{search_missing:,}"
)


search_duplicates = con.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT reep_id
        FROM player_search
        GROUP BY reep_id
        HAVING COUNT(*) > 1
    )
""").fetchone()[0]

check(
    "Duplicate search-index REEP IDs",
    search_duplicates == 0,
    f"{search_duplicates:,}"
)


search_count_mismatch = con.execute("""
    SELECT COUNT(*)
    FROM player_search s

    LEFT JOIN (
        SELECT
            reep_id,
            COUNT(*) AS alias_count
        FROM player_aliases
        GROUP BY reep_id
    ) a
        ON s.reep_id = a.reep_id

    LEFT JOIN (
        SELECT
            reep_id,
            COUNT(*) AS external_id_count
        FROM player_external_ids
        GROUP BY reep_id
    ) e
        ON s.reep_id = e.reep_id

    WHERE
        s.alias_count
            <> COALESCE(a.alias_count, 0)

        OR

        s.external_id_count
            <> COALESCE(e.external_id_count, 0)
""").fetchone()[0]

check(
    "Search alias/external-ID counts accurate",
    search_count_mismatch == 0,
    f"{search_count_mismatch:,}"
)


search_null_ids = null_or_empty_count(
    con,
    "player_search",
    "reep_id"
)

check(
    "Search null/empty REEP IDs",
    search_null_ids == 0,
    f"{search_null_ids:,}"
)


# ================================================================
# 13. SEARCH TEXT BASIC INTEGRITY
# ================================================================

section("13. SEARCH TEXT INTEGRITY")

search_text_missing = con.execute("""
    SELECT COUNT(*)
    FROM player_search
    WHERE
        search_text IS NULL
        OR TRIM(search_text) = ''
""").fetchone()[0]

check(
    "Empty search_text values",
    search_text_missing == 0,
    f"{search_text_missing:,}"
)


# ================================================================
# 14. METADATA INTEGRITY
# ================================================================

section("14. DATABASE METADATA INTEGRITY")

metadata_null_keys = null_or_empty_count(
    con,
    "database_metadata",
    "key"
)

check(
    "Metadata null/empty keys",
    metadata_null_keys == 0,
    f"{metadata_null_keys:,}"
)


metadata_duplicate_keys = con.execute("""
    SELECT COUNT(*)
    FROM (
        SELECT key
        FROM database_metadata
        GROUP BY key
        HAVING COUNT(*) > 1
    )
""").fetchone()[0]

check(
    "Duplicate metadata keys",
    metadata_duplicate_keys == 0,
    f"{metadata_duplicate_keys:,}"
)


metadata_version = con.execute("""
    SELECT value
    FROM database_metadata
    WHERE key = 'schema_version'
""").fetchone()


check(
    "Schema version is REEP V1.2",
    metadata_version is not None
    and metadata_version[0] == "REEP V1.2",
    str(metadata_version[0])
    if metadata_version
    else "missing"
)


# ================================================================
# 15. POSITION PROVIDER CHECK
# ================================================================

section("15. POSITION PROVIDER INTEGRITY")

provider_count = con.execute("""
    SELECT COUNT(DISTINCT provider)
    FROM player_position_claims
""").fetchone()[0]

provider_names = [
    row[0]
    for row in con.execute("""
        SELECT DISTINCT provider
        FROM player_position_claims
        ORDER BY provider
    """).fetchall()
]

print(
    f"Position providers: {provider_names}"
)

check(
    "Position provider count",
    provider_count == 1,
    f"{provider_count:,}"
)

check(
    "Transfermarkt position provider present",
    "transfermarkt" in [
        str(x).lower()
        for x in provider_names
    ],
    str(provider_names)
)


# ================================================================
# 16. POSITION STATUS SUMMARY
# ================================================================

section("16. POSITION STATUS SUMMARY")

position_status_rows = con.execute("""
    SELECT
        position_status,
        COUNT(*)
    FROM player_position
    GROUP BY position_status
    ORDER BY position_status
""").fetchall()

for status, total in position_status_rows:

    print(
        f"{str(status):<20} {total:>10,}"
    )


# ================================================================
# 17. POSITION CLAIM TYPE SUMMARY
# ================================================================

section("17. POSITION CLAIM TYPE SUMMARY")

position_type_rows = con.execute("""
    SELECT
        position_type,
        COUNT(*)
    FROM player_position_claims
    GROUP BY position_type
    ORDER BY position_type
""").fetchall()

for position_type, total in position_type_rows:

    print(
        f"{str(position_type):<20} {total:>10,}"
    )


# ================================================================
# 18. SOURCE/PROVENANCE SUMMARY
# ================================================================

section("18. DATA PROVENANCE SUMMARY")

alias_sources = con.execute("""
    SELECT
        source,
        COUNT(*)
    FROM player_aliases
    GROUP BY source
    ORDER BY source
""").fetchall()

print()
print("Alias sources:")

for source, total in alias_sources:

    print(
        f"  {str(source):<25} {total:>12,}"
    )


external_sources = con.execute("""
    SELECT
        source,
        COUNT(*)
    FROM player_external_ids
    GROUP BY source
    ORDER BY source
""").fetchall()

print()
print("External-ID sources:")

for source, total in external_sources:

    print(
        f"  {str(source):<25} {total:>12,}"
    )


# ================================================================
# 19. FINAL DATABASE SIZE / TABLE INVENTORY
# ================================================================

section("19. FINAL DATABASE INVENTORY")

print()

for table in REQUIRED_TABLES:

    if table not in existing_tables:
        continue

    total = count(
        con,
        table
    )

    print(
        f"{table:<32} {total:>12,}"
    )


# ================================================================
# FINAL RESULT
# ================================================================

section("FINAL AUDIT RESULT")

print()
print(
    f"Checks passed : {PASS_COUNT:,}"
)

print(
    f"Checks failed : {FAIL_COUNT:,}"
)

print(
    f"Warnings      : {WARN_COUNT:,}"
)

print()

if FAIL_COUNT == 0:

    print("=" * 80)
    print("FINAL STATUS: PASS")
    print("=" * 80)

    print()
    print(
        "REEP PLAYER MASTER V1.2 PASSED THE FINAL "
        "INTEGRITY AUDIT."
    )

    print()
    print(
        "The database is structurally ready for "
        "production use."
    )

    print()
    print("Database:")
    print(DATABASE)

else:

    print("=" * 80)
    print("FINAL STATUS: FAIL")
    print("=" * 80)

    print()
    print(
        "One or more integrity checks failed."
    )

    print(
        "DO NOT mark the database production-ready "
        "until the failures are reviewed."
    )


# ================================================================
# CLOSE
# ================================================================

con.close()

print()
print("Audit complete.")