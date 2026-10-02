import duckdb
from pathlib import Path
import json

# ============================================================
# REEP CLEAN PLAYER MASTER BUILDER
# ============================================================
#
# STAGE 10
#
# PURPOSE:
#   Build a clean REEP-only football player master database.
#
# SOURCE:
#   reep-register-v1.duckdb
#
# OUTPUT:
#   output/reep-player-master.duckdb
#
# IMPORTANT:
#   - Source database is opened READ-ONLY.
#   - Source database is NEVER modified.
#   - Only canonical REEP players are included.
#   - Coach observed-club rows are excluded.
#   - Country is intentionally excluded because the audited
#     player country field is 0% populated.
#
# OUTPUT TABLES:
#   1. players
#   2. aliases
#   3. external_ids
#   4. observed_clubs
#   5. database_metadata
#
# ============================================================


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = Path("output")

OUTPUT_DB = OUTPUT_DIR / "reep-player-master.duckdb"

OUTPUT_REPORT = OUTPUT_DIR / "reep-player-master-build-report.json"


# ------------------------------------------------------------
# START
# ------------------------------------------------------------

print("=" * 70)
print("REEP CLEAN PLAYER MASTER BUILDER")
print("=" * 70)
print()

print("SOURCE DATABASE:")
print(SOURCE_DB)

print()

print("OUTPUT DATABASE:")
print(OUTPUT_DB)

print()

print("SOURCE WILL BE OPENED READ-ONLY.")
print("SOURCE DATABASE WILL NOT BE MODIFIED.")
print()


# ------------------------------------------------------------
# CREATE OUTPUT DIRECTORY
# ------------------------------------------------------------

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ------------------------------------------------------------
# CHECK SOURCE DATABASE
# ------------------------------------------------------------

if not SOURCE_DB.exists():

    print("ERROR: Source database was not found.")
    print()

    print(
        "Expected source database:"
    )

    print(SOURCE_DB)

    raise SystemExit(1)


# ------------------------------------------------------------
# PREVENT ACCIDENTAL OVERWRITE
# ------------------------------------------------------------

if OUTPUT_DB.exists():

    print("=" * 70)
    print("EXISTING OUTPUT DATABASE FOUND")
    print("=" * 70)
    print()

    print(
        f"Existing file:"
    )

    print(OUTPUT_DB)

    print()

    answer = input(
        "Replace existing output database? "
        "Type YES to continue: "
    ).strip()

    if answer != "YES":

        print()
        print("Build cancelled.")
        raise SystemExit(0)

    print()

    print("Removing previous generated output database...")

    try:

        OUTPUT_DB.unlink()

    except Exception as exc:

        print()
        print(
            "ERROR: Could not remove the existing output database."
        )

        print(exc)

        raise SystemExit(1)

    print(
        "Previous output database removed."
    )

    print()


# ------------------------------------------------------------
# CONNECT TO SOURCE READ-ONLY
# ------------------------------------------------------------

print("=" * 70)
print("OPENING SOURCE DATABASE")
print("=" * 70)
print()

print(
    "Opening REEP source database READ-ONLY..."
)

source = duckdb.connect(
    database=str(SOURCE_DB),
    read_only=True
)

print(
    "Source database connected successfully."
)

print()


# ------------------------------------------------------------
# VERIFY REQUIRED SOURCE TABLES
# ------------------------------------------------------------

required_tables = [
    "players",
    "entities",
    "aliases",
    "bridges",
    "observed_clubs",
]


existing_tables = {
    row[0]
    for row in source.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        """
    ).fetchall()
}


print("=" * 70)
print("VERIFYING REQUIRED SOURCE TABLES")
print("=" * 70)
print()


missing_tables = []

for table in required_tables:

    if table in existing_tables:

        print(
            f"  {table:<20} FOUND"
        )

    else:

        print(
            f"  {table:<20} MISSING"
        )

        missing_tables.append(table)


print()


if missing_tables:

    source.close()

    print(
        "ERROR: Required source tables are missing:"
    )

    for table in missing_tables:

        print(
            f"  - {table}"
        )

    raise SystemExit(1)


# ------------------------------------------------------------
# SOURCE PLAYER COUNT
# ------------------------------------------------------------

source_player_count = source.execute(
    """
    SELECT COUNT(*)
    FROM main.players
    """
).fetchone()[0]


print("=" * 70)
print("SOURCE PLAYER COUNT")
print("=" * 70)
print()

print(
    f"Source REEP players: {source_player_count:,}"
)

print()

if source_player_count != 432124:

    print(
        "WARNING:"
    )

    print(
        "Previous audits recorded 432,124 players."
    )

    print(
        f"Current source count: {source_player_count:,}"
    )

    print()


# ------------------------------------------------------------
# CREATE OUTPUT DATABASE
# ------------------------------------------------------------

print("=" * 70)
print("CREATING OUTPUT DATABASE")
print("=" * 70)
print()


target = duckdb.connect(
    database=str(OUTPUT_DB)
)


print(
    "Output database created."
)

print()


# ------------------------------------------------------------
# ATTACH SOURCE DATABASE READ-ONLY
# ------------------------------------------------------------

print(
    "Attaching source database READ-ONLY..."
)

target.execute(
    f"""
    ATTACH '{SOURCE_DB.as_posix()}' AS source_db
    (READ_ONLY)
    """
)

print(
    "Source database attached READ-ONLY."
)

print()


# ============================================================
# 1. PLAYERS
# ============================================================

print("=" * 70)
print("BUILDING players TABLE")
print("=" * 70)
print()


target.execute(
    """
    CREATE TABLE players AS

    SELECT
        p.reep_id,

        'player' AS entity_type,

        p.status,

        p.label,

        p.gender,

        e.corroboration_grade,

        e.corroboration_count,

        e.source_tier_band

    FROM source_db.main.players p

    LEFT JOIN source_db.main.entities e

      ON e.reep_id = p.reep_id

     AND e.entity_type = 'player'
    """
)


player_count = target.execute(
    """
    SELECT COUNT(*)
    FROM players
    """
).fetchone()[0]


print(
    f"Players created: {player_count:,}"
)

print()


# ============================================================
# 2. ALIASES
# ============================================================

print("=" * 70)
print("BUILDING aliases TABLE")
print("=" * 70)
print()


target.execute(
    """
    CREATE TABLE aliases AS

    SELECT
        a.reep_id,

        a.alias,

        a.kind,

        a.rank,

        a.language

    FROM source_db.main.aliases a

    INNER JOIN players p

      ON p.reep_id = a.reep_id
    """
)


alias_count = target.execute(
    """
    SELECT COUNT(*)
    FROM aliases
    """
).fetchone()[0]


alias_player_count = target.execute(
    """
    SELECT COUNT(DISTINCT reep_id)
    FROM aliases
    """
).fetchone()[0]


print(
    f"Alias rows created: {alias_count:,}"
)

print(
    f"Players with aliases: {alias_player_count:,}"
)

print()


# ============================================================
# 3. EXTERNAL IDS
# ============================================================

print("=" * 70)
print("BUILDING external_ids TABLE")
print("=" * 70)
print()


target.execute(
    """
    CREATE TABLE external_ids AS

    SELECT
        b.provider,

        b.namespace,

        b.external_id,

        b.reep_id,

        b.rung

    FROM source_db.main.bridges b

    INNER JOIN players p

      ON p.reep_id = b.reep_id
    """
)


external_id_count = target.execute(
    """
    SELECT COUNT(*)
    FROM external_ids
    """
).fetchone()[0]


external_id_player_count = target.execute(
    """
    SELECT COUNT(DISTINCT reep_id)
    FROM external_ids
    """
).fetchone()[0]


print(
    f"External-ID / bridge rows created: "
    f"{external_id_count:,}"
)

print(
    f"Players with external IDs: "
    f"{external_id_player_count:,}"
)

print()


# ============================================================
# 4. OBSERVED CLUB EVIDENCE
# ============================================================

print("=" * 70)
print("BUILDING observed_clubs TABLE")
print("=" * 70)
print()


target.execute(
    """
    CREATE TABLE observed_clubs AS

    SELECT
        oc.reep_id,

        oc.observed_clubs,

        oc.first_observed_season,

        oc.last_observed_season,

        oc.basis

    FROM source_db.main.observed_clubs oc

    INNER JOIN players p

      ON p.reep_id = oc.reep_id

    WHERE oc.entity_type = 'player'
    """
)


club_count = target.execute(
    """
    SELECT COUNT(*)
    FROM observed_clubs
    """
).fetchone()[0]


club_player_count = target.execute(
    """
    SELECT COUNT(DISTINCT reep_id)
    FROM observed_clubs
    """
).fetchone()[0]


print(
    f"Player observed-club rows created: "
    f"{club_count:,}"
)

print(
    f"Players with observed-club evidence: "
    f"{club_player_count:,}"
)

print()

print(
    "IMPORTANT:"
)

print(
    "Observed-club evidence is NOT a complete career history."
)

print(
    "It represents clubs this person appears for in the"
)

print(
    "register's own match coverage."
)

print()


# ============================================================
# 5. DATABASE METADATA
# ============================================================

print("=" * 70)
print("BUILDING database_metadata TABLE")
print("=" * 70)
print()


target.execute(
    """
    CREATE TABLE database_metadata (

        key VARCHAR,

        value VARCHAR

    )
    """
)


metadata = [

    (
        "database_name",
        "REEP Clean Player Master"
    ),

    (
        "database_version",
        "1.0"
    ),

    (
        "source_database",
        "reep-register-v1.duckdb"
    ),

    (
        "source_player_count",
        str(source_player_count)
    ),

    (
        "output_player_count",
        str(player_count)
    ),

    (
        "alias_count",
        str(alias_count)
    ),

    (
        "external_id_count",
        str(external_id_count)
    ),

    (
        "observed_club_count",
        str(club_count)
    ),

    (
        "players_with_aliases",
        str(alias_player_count)
    ),

    (
        "players_with_external_ids",
        str(external_id_player_count)
    ),

    (
        "players_with_observed_clubs",
        str(club_player_count)
    ),

    (
        "career_history_complete",
        "false"
    ),

    (
        "club_evidence_basis",
        "clubs this person appears for in the register's own match coverage; not a complete career history"
    ),

    (
        "country_field_included",
        "false"
    ),

    (
        "coach_records_in_player_master",
        "false"
    ),

    (
        "source_read_only",
        "true"
    ),
]


target.executemany(
    """
    INSERT INTO database_metadata
    VALUES (?, ?)
    """,
    metadata
)


print(
    "Metadata created."
)

print()


# ============================================================
# 6. INDEXES
# ============================================================

print("=" * 70)
print("CREATING INDEXES")
print("=" * 70)
print()


target.execute(
    """
    CREATE UNIQUE INDEX idx_players_reep_id
    ON players(reep_id)
    """
)


target.execute(
    """
    CREATE INDEX idx_players_label
    ON players(label)
    """
)


target.execute(
    """
    CREATE INDEX idx_aliases_reep_id
    ON aliases(reep_id)
    """
)


target.execute(
    """
    CREATE INDEX idx_aliases_alias
    ON aliases(alias)
    """
)


target.execute(
    """
    CREATE INDEX idx_external_ids_reep_id
    ON external_ids(reep_id)
    """
)


target.execute(
    """
    CREATE INDEX idx_external_ids_external_id
    ON external_ids(external_id)
    """
)


target.execute(
    """
    CREATE INDEX idx_observed_clubs_reep_id
    ON observed_clubs(reep_id)
    """
)


print(
    "Indexes created."
)

print()


# ============================================================
# CLOSE TARGET
# ============================================================

print(
    "Closing output database..."
)

target.close()

print(
    "Output database closed."
)

print()


# ============================================================
# CLOSE SOURCE
# ============================================================

print(
    "Closing source database..."
)

source.close()

print(
    "Source database closed."
)

print()


# ============================================================
# REOPEN OUTPUT FOR VALIDATION
# ============================================================

print("=" * 70)
print("REOPENING OUTPUT DATABASE FOR VALIDATION")
print("=" * 70)
print()


check = duckdb.connect(
    database=str(OUTPUT_DB),
    read_only=True
)


# ============================================================
# OUTPUT TABLES
# ============================================================

output_tables = {
    row[0]

    for row in check.execute(
        """
        SELECT table_name

        FROM information_schema.tables

        WHERE table_schema = 'main'
        """
    ).fetchall()
}


print(
    "Output tables:"
)

print()


for table in sorted(output_tables):

    print(
        f"  {table}"
    )

print()


# ============================================================
# OUTPUT COUNTS
# ============================================================

print("=" * 70)
print("OUTPUT COUNTS")
print("=" * 70)
print()


counts = {}


for table in [
    "players",
    "aliases",
    "external_ids",
    "observed_clubs",
]:

    if table not in output_tables:

        print(
            f"ERROR: Missing output table: {table}"
        )

        check.close()

        raise SystemExit(1)


    count = check.execute(
        f"""
        SELECT COUNT(*)
        FROM "{table}"
        """
    ).fetchone()[0]


    counts[table] = count


    print(
        f"{table:<20} {count:,}"
    )


print()


# ============================================================
# PLAYER VALIDATION
# ============================================================

print("=" * 70)
print("PLAYER VALIDATION")
print("=" * 70)
print()


duplicate_players = check.execute(
    """
    SELECT COUNT(*)

    FROM (

        SELECT reep_id

        FROM players

        GROUP BY reep_id

        HAVING COUNT(*) > 1

    )
    """
).fetchone()[0]


null_player_ids = check.execute(
    """
    SELECT COUNT(*)

    FROM players

    WHERE reep_id IS NULL

       OR TRIM(reep_id) = ''
    """
).fetchone()[0]


non_player_rows = check.execute(
    """
    SELECT COUNT(*)

    FROM players

    WHERE entity_type <> 'player'
    """
).fetchone()[0]


null_labels = check.execute(
    """
    SELECT COUNT(*)

    FROM players

    WHERE label IS NULL

       OR TRIM(label) = ''
    """
).fetchone()[0]


null_status = check.execute(
    """
    SELECT COUNT(*)

    FROM players

    WHERE status IS NULL

       OR TRIM(status) = ''
    """
).fetchone()[0]


print(
    f"Duplicate player IDs:       {duplicate_players:,}"
)

print(
    f"NULL/empty player IDs:       {null_player_ids:,}"
)

print(
    f"Non-player rows:             {non_player_rows:,}"
)

print(
    f"NULL/empty labels:           {null_labels:,}"
)

print(
    f"NULL/empty status:           {null_status:,}"
)

print()


# ============================================================
# CHILD TABLE ORPHAN VALIDATION
# ============================================================

print("=" * 70)
print("CHILD TABLE VALIDATION")
print("=" * 70)
print()


orphan_aliases = check.execute(
    """
    SELECT COUNT(*)

    FROM aliases a

    LEFT JOIN players p

      ON p.reep_id = a.reep_id

    WHERE p.reep_id IS NULL
    """
).fetchone()[0]


orphan_external_ids = check.execute(
    """
    SELECT COUNT(*)

    FROM external_ids e

    LEFT JOIN players p

      ON p.reep_id = e.reep_id

    WHERE p.reep_id IS NULL
    """
).fetchone()[0]


orphan_clubs = check.execute(
    """
    SELECT COUNT(*)

    FROM observed_clubs oc

    LEFT JOIN players p

      ON p.reep_id = oc.reep_id

    WHERE p.reep_id IS NULL
    """
).fetchone()[0]


print(
    f"Orphan alias rows:           {orphan_aliases:,}"
)

print(
    f"Orphan external-ID rows:     {orphan_external_ids:,}"
)

print(
    f"Orphan club rows:             {orphan_clubs:,}"
)

print()


# ============================================================
# CLUB EVIDENCE VALIDATION
# ============================================================

print("=" * 70)
print("CLUB EVIDENCE VALIDATION")
print("=" * 70)
print()


club_player_ids = check.execute(
    """
    SELECT COUNT(DISTINCT reep_id)

    FROM observed_clubs
    """
).fetchone()[0]


club_duplicate_ids = check.execute(
    """
    SELECT COUNT(*)

    FROM (

        SELECT reep_id

        FROM observed_clubs

        GROUP BY reep_id

        HAVING COUNT(*) > 1

    )
    """
).fetchone()[0]


print(
    f"Players with club evidence:  {club_player_ids:,}"
)

print(
    f"Duplicate club player IDs:   {club_duplicate_ids:,}"
)

print()


# ============================================================
# ALIAS VALIDATION
# ============================================================

print("=" * 70)
print("ALIAS VALIDATION")
print("=" * 70)
print()


alias_distinct_players = check.execute(
    """
    SELECT COUNT(DISTINCT reep_id)

    FROM aliases
    """
).fetchone()[0]


null_alias_ids = check.execute(
    """
    SELECT COUNT(*)

    FROM aliases

    WHERE reep_id IS NULL

       OR TRIM(reep_id) = ''
    """
).fetchone()[0]


print(
    f"Alias rows:                  {alias_count:,}"
)

print(
    f"Players with aliases:        {alias_distinct_players:,}"
)

print(
    f"NULL/empty alias player IDs:  {null_alias_ids:,}"
)

print()


# ============================================================
# EXTERNAL-ID VALIDATION
# ============================================================

print("=" * 70)
print("EXTERNAL-ID VALIDATION")
print("=" * 70)
print()


external_distinct_players = check.execute(
    """
    SELECT COUNT(DISTINCT reep_id)

    FROM external_ids
    """
).fetchone()[0]


null_external_ids = check.execute(
    """
    SELECT COUNT(*)

    FROM external_ids

    WHERE reep_id IS NULL

       OR TRIM(reep_id) = ''

       OR external_id IS NULL

       OR TRIM(external_id) = ''
    """
).fetchone()[0]


print(
    f"External-ID rows:            {external_id_count:,}"
)

print(
    f"Players with external IDs:   {external_distinct_players:,}"
)

print(
    f"NULL/empty external IDs:     {null_external_ids:,}"
)

print()


# ============================================================
# EXPECTED COUNT CHECKS
# ============================================================

print("=" * 70)
print("EXPECTED COUNT CHECKS")
print("=" * 70)
print()


expected_players = 432124

expected_aliases = 597522

expected_external_ids = 2789713

expected_club_rows = 142518


print(
    f"Expected players:             {expected_players:,}"
)

print(
    f"Actual players:               {player_count:,}"
)

print()


print(
    f"Expected alias rows:          {expected_aliases:,}"
)

print(
    f"Actual alias rows:            {alias_count:,}"
)

print()


print(
    f"Expected external-ID rows:    {expected_external_ids:,}"
)

print(
    f"Actual external-ID rows:      {external_id_count:,}"
)

print()


print(
    f"Expected club rows:           {expected_club_rows:,}"
)

print(
    f"Actual club rows:             {club_count:,}"
)

print()


expected_counts_match = (

    player_count == expected_players

    and alias_count == expected_aliases

    and external_id_count == expected_external_ids

    and club_count == expected_club_rows
)


if expected_counts_match:

    print(
        "Expected counts: PASS"
    )

else:

    print(
        "Expected counts: REVIEW REQUIRED"
    )

print()


# ============================================================
# FINAL BUILD STATUS
# ============================================================

build_pass = (

    player_count == source_player_count

    and duplicate_players == 0

    and null_player_ids == 0

    and non_player_rows == 0

    and null_labels == 0

    and null_status == 0

    and orphan_aliases == 0

    and orphan_external_ids == 0

    and orphan_clubs == 0

    and club_duplicate_ids == 0

    and null_alias_ids == 0

    and null_external_ids == 0

    and expected_counts_match
)


if build_pass:

    status = "PASS"

else:

    status = "REVIEW_REQUIRED"


print("=" * 70)
print(
    f"FINAL BUILD STATUS: {status}"
)
print("=" * 70)
print()


# ============================================================
# BUILD REPORT
# ============================================================

report = {

    "build": {

        "name":
            "REEP Clean Player Master",

        "version":
            "1.0",

        "source_database":
            str(SOURCE_DB),

        "output_database":
            str(OUTPUT_DB),

        "source_read_only":
            True,

    },

    "source": {

        "player_count":
            source_player_count,

    },

    "output_counts": counts,

    "expected_counts": {

        "players":
            expected_players,

        "aliases":
            expected_aliases,

        "external_ids":
            expected_external_ids,

        "observed_clubs":
            expected_club_rows,

    },

    "coverage": {

        "players_with_aliases":
            alias_distinct_players,

        "players_with_external_ids":
            external_distinct_players,

        "players_with_observed_clubs":
            club_player_ids,

    },

    "validation": {

        "duplicate_player_ids":
            duplicate_players,

        "null_or_empty_player_ids":
            null_player_ids,

        "non_player_rows":
            non_player_rows,

        "null_or_empty_labels":
            null_labels,

        "null_or_empty_status":
            null_status,

        "orphan_aliases":
            orphan_aliases,

        "orphan_external_ids":
            orphan_external_ids,

        "orphan_clubs":
            orphan_clubs,

        "duplicate_club_player_ids":
            club_duplicate_ids,

        "null_or_empty_alias_player_ids":
            null_alias_ids,

        "null_or_empty_external_ids":
            null_external_ids,

        "expected_counts_match":
            expected_counts_match,

    },

    "status":
        status,

}


with open(
    OUTPUT_REPORT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        report,
        f,
        indent=2,
        ensure_ascii=False
    )


check.close()


# ============================================================
# COMPLETE
# ============================================================

print(
    "Build report:"
)

print(
    OUTPUT_REPORT
)

print()

print(
    "SOURCE DATABASE WAS NOT MODIFIED."
)

print()

print("=" * 70)
print("STAGE 10 COMPLETE")
print("=" * 70)