import duckdb
from pathlib import Path
from datetime import datetime, timezone

# ================================================================
# REEP V1.2 — FINAL PLAYER MASTER BUILD
# ================================================================
#
# READ-ONLY SOURCES:
#   - Original REEP Register
#   - Audited position evidence database
#
# OUTPUT:
#   output/reep-player-master-v1.2.duckdb
#
# The source databases are NEVER modified.
# ================================================================

SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

POSITION_DB = Path(
    r"output\reep-player-position-evidence.duckdb"
)

OUTPUT_DB = Path(
    r"output\reep-player-master-v1.2.duckdb"
)

SCHEMA_VERSION = "REEP V1.2"


# ================================================================
# HELPERS
# ================================================================

def header(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def table_count(con, table):

    return con.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]


# ================================================================
# INITIALIZE FINAL DATABASE
# ================================================================

def initialize_database(con):

    con.execute("""
        CREATE TABLE players (
            reep_id VARCHAR NOT NULL PRIMARY KEY,
            status VARCHAR,
            label VARCHAR,
            gender VARCHAR,
            country VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE player_aliases (
            reep_id VARCHAR NOT NULL,
            alias VARCHAR NOT NULL,
            alias_kind VARCHAR,
            language VARCHAR,
            source VARCHAR NOT NULL,
            confidence VARCHAR,
            rank VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE player_external_ids (
            reep_id VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            namespace VARCHAR,
            external_id VARCHAR NOT NULL,
            property VARCHAR,
            rank VARCHAR,
            confidence VARCHAR,
            source VARCHAR NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE player_redirects (
            from_id VARCHAR NOT NULL,
            to_id VARCHAR NOT NULL,
            reason VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE player_club_evidence (
            reep_id VARCHAR NOT NULL,
            entity_type VARCHAR,
            observed_clubs VARCHAR,
            first_observed_season VARCHAR,
            last_observed_season VARCHAR,
            basis VARCHAR
        )
    """)

    con.execute("""
        CREATE TABLE player_position (
            reep_id VARCHAR NOT NULL PRIMARY KEY,
            label VARCHAR NOT NULL,
            primary_position VARCHAR,
            secondary_positions VARCHAR,
            position_status VARCHAR NOT NULL,
            evidence_count INTEGER NOT NULL,
            provider_count INTEGER NOT NULL,
            source VARCHAR NOT NULL,
            updated_at VARCHAR NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE player_position_claims (
            reep_id VARCHAR NOT NULL,
            label VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            provider_namespace VARCHAR NOT NULL,
            provider_id VARCHAR NOT NULL,
            position VARCHAR NOT NULL,
            position_normalized VARCHAR NOT NULL,
            position_type VARCHAR NOT NULL,
            source_url VARCHAR NOT NULL,
            http_status INTEGER,
            parser_version VARCHAR NOT NULL,
            retrieved_at VARCHAR NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE player_search (
            reep_id VARCHAR NOT NULL PRIMARY KEY,
            label VARCHAR,
            search_text VARCHAR,
            alias_count INTEGER NOT NULL,
            external_id_count INTEGER NOT NULL
        )
    """)

    con.execute("""
        CREATE TABLE database_metadata (
            key VARCHAR NOT NULL PRIMARY KEY,
            value VARCHAR
        )
    """)

    # ------------------------------------------------------------
    # Indexes
    # ------------------------------------------------------------

    con.execute("""
        CREATE INDEX idx_player_aliases_reep_id
        ON player_aliases(reep_id)
    """)

    con.execute("""
        CREATE INDEX idx_player_aliases_alias
        ON player_aliases(alias)
    """)

    con.execute("""
        CREATE INDEX idx_player_external_ids_reep_id
        ON player_external_ids(reep_id)
    """)

    con.execute("""
        CREATE INDEX idx_player_external_ids_provider
        ON player_external_ids(provider)
    """)

    con.execute("""
        CREATE INDEX idx_player_external_ids_external_id
        ON player_external_ids(external_id)
    """)

    con.execute("""
        CREATE INDEX idx_player_redirects_from
        ON player_redirects(from_id)
    """)

    con.execute("""
        CREATE INDEX idx_player_redirects_to
        ON player_redirects(to_id)
    """)

    con.execute("""
        CREATE INDEX idx_player_club_evidence_reep_id
        ON player_club_evidence(reep_id)
    """)

    con.execute("""
        CREATE INDEX idx_position_claims_reep_id
        ON player_position_claims(reep_id)
    """)


# ================================================================
# MAIN BUILD
# ================================================================

def main():

    header("REEP V1.2 — FINAL PLAYER MASTER BUILD")

    print()
    print("SOURCE DATABASE:")
    print(SOURCE_DB)

    print()
    print("POSITION DATABASE:")
    print(POSITION_DB)

    print()
    print("OUTPUT DATABASE:")
    print(OUTPUT_DB)

    print()
    print("SOURCE MODE: READ-ONLY")

    # ------------------------------------------------------------
    # Safety checks
    # ------------------------------------------------------------

    if OUTPUT_DB.exists():

        print()
        print("ERROR: Output database already exists:")
        print(OUTPUT_DB)
        print()
        print("No changes were made.")
        print()
        print(
            "Delete or rename the existing output database "
            "only if you intentionally want to rebuild it."
        )

        return

    if not SOURCE_DB.exists():

        raise FileNotFoundError(
            f"Source database not found: {SOURCE_DB}"
        )

    if not POSITION_DB.exists():

        raise FileNotFoundError(
            f"Position database not found: {POSITION_DB}"
        )

    OUTPUT_DB.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ------------------------------------------------------------
    # Open output database
    # ------------------------------------------------------------

    output = duckdb.connect(
        str(OUTPUT_DB)
    )

    # ------------------------------------------------------------
    # Attach source databases READ-ONLY
    # ------------------------------------------------------------

    output.execute(
        f"ATTACH '{SOURCE_DB.as_posix()}' "
        f"AS source (READ_ONLY)"
    )

    output.execute(
        f"ATTACH '{POSITION_DB.as_posix()}' "
        f"AS position (READ_ONLY)"
    )

    initialize_database(output)

    print()
    print("All databases opened successfully.")

    # ============================================================
    # 1. PLAYERS
    # ============================================================

    header("1. BUILDING PLAYERS")

    output.execute("""
        INSERT INTO players
        SELECT
            reep_id,
            status,
            label,
            gender,
            country
        FROM source.players
    """)

    players_count = table_count(
        output,
        "players"
    )

    print(
        f"Canonical players imported: "
        f"{players_count:,}"
    )

    # ============================================================
    # 2. PLAYER ALIASES
    # ============================================================

    header("2. BUILDING PLAYER ALIASES")

    # ------------------------------------------------------------
    # Original REEP aliases
    # ------------------------------------------------------------

    output.execute("""
        INSERT INTO player_aliases
        SELECT DISTINCT
            a.reep_id,
            TRIM(a.alias),
            a.kind,
            a.language,
            'reep_aliases',
            NULL,
            a.rank
        FROM source.aliases a
        INNER JOIN players p
            ON a.reep_id = p.reep_id
        WHERE
            a.alias IS NOT NULL
            AND TRIM(a.alias) <> ''
    """)

    # ------------------------------------------------------------
    # Overlay aliases
    # ------------------------------------------------------------

    output.execute("""
        INSERT INTO player_aliases
        SELECT DISTINCT
            o.reep_id,
            TRIM(o.name),
            'overlay',
            o.language,
            COALESCE(
                NULLIF(TRIM(o.name_source), ''),
                'overlay_aliases'
            ),
            o.confidence,
            NULL
        FROM source.overlay_aliases o
        INNER JOIN players p
            ON o.reep_id = p.reep_id
        WHERE
            o.name IS NOT NULL
            AND TRIM(o.name) <> ''
    """)

    aliases_count = table_count(
        output,
        "player_aliases"
    )

    print(
        f"Player alias rows: "
        f"{aliases_count:,}"
    )

    # ============================================================
    # 3. PLAYER EXTERNAL IDS
    # ============================================================

    header("3. BUILDING PLAYER EXTERNAL IDS")

    # ------------------------------------------------------------
    # REEP bridges
    # ------------------------------------------------------------

    output.execute("""
        INSERT INTO player_external_ids
        SELECT DISTINCT
            b.reep_id,
            TRIM(b.provider),
            TRIM(b.namespace),
            TRIM(b.external_id),
            NULL,
            b.rung,
            NULL,
            'bridges'
        FROM source.bridges b
        INNER JOIN players p
            ON b.reep_id = p.reep_id
        WHERE
            b.provider IS NOT NULL
            AND TRIM(b.provider) <> ''
            AND b.external_id IS NOT NULL
            AND TRIM(b.external_id) <> ''
    """)

    # ------------------------------------------------------------
    # Overlay XIDs
    # ------------------------------------------------------------

    output.execute("""
        INSERT INTO player_external_ids
        SELECT DISTINCT
            x.reep_id,
            TRIM(x.provider),
            NULL,
            TRIM(x.external_id),
            TRIM(x.property),
            x.rank,
            x.confidence,
            'overlay_xids'
        FROM source.overlay_xids x
        INNER JOIN players p
            ON x.reep_id = p.reep_id
        WHERE
            x.provider IS NOT NULL
            AND TRIM(x.provider) <> ''
            AND x.external_id IS NOT NULL
            AND TRIM(x.external_id) <> ''
    """)

    external_ids_count = table_count(
        output,
        "player_external_ids"
    )

    print(
        f"External-ID rows: "
        f"{external_ids_count:,}"
    )

    # ============================================================
    # 4. PLAYER REDIRECTS
    # ============================================================

    header("4. BUILDING PLAYER REDIRECTS")

    output.execute("""
        INSERT INTO player_redirects
        SELECT DISTINCT
            r.from_id,
            r.to_id,
            r.reason
        FROM source.redirects r
        WHERE
            r.from_id IS NOT NULL
            AND TRIM(r.from_id) <> ''
            AND r.to_id IS NOT NULL
            AND TRIM(r.to_id) <> ''
            AND (
                EXISTS (
                    SELECT 1
                    FROM players p
                    WHERE p.reep_id = r.from_id
                )
                OR EXISTS (
                    SELECT 1
                    FROM players p
                    WHERE p.reep_id = r.to_id
                )
            )
    """)

    redirects_count = table_count(
        output,
        "player_redirects"
    )

    print(
        f"Player-related redirects: "
        f"{redirects_count:,}"
    )

    # ============================================================
    # 5. PLAYER CLUB EVIDENCE
    # ============================================================

    header("5. BUILDING PLAYER CLUB EVIDENCE")

    output.execute("""
        INSERT INTO player_club_evidence
        SELECT
            o.reep_id,
            o.entity_type,
            o.observed_clubs,
            o.first_observed_season,
            o.last_observed_season,
            o.basis
        FROM source.observed_clubs o
        INNER JOIN players p
            ON o.reep_id = p.reep_id
        WHERE
            LOWER(TRIM(o.entity_type)) = 'player'
    """)

    club_count = table_count(
        output,
        "player_club_evidence"
    )

    print(
        f"Player club-evidence rows: "
        f"{club_count:,}"
    )

    # ============================================================
    # 6. POSITION MASTER
    # ============================================================

    header("6. IMPORTING POSITION MASTER")

    output.execute("""
        INSERT INTO player_position
        SELECT
            pp.reep_id,
            pp.label,
            pp.primary_position,
            pp.secondary_positions,
            pp.position_status,
            pp.evidence_count,
            pp.provider_count,
            pp.source,
            pp.updated_at
        FROM position.player_position pp
        INNER JOIN players p
            ON pp.reep_id = p.reep_id
    """)

    position_count = table_count(
        output,
        "player_position"
    )

    print(
        f"Position master rows: "
        f"{position_count:,}"
    )

    # ============================================================
    # 7. POSITION CLAIMS
    # ============================================================

    header("7. IMPORTING POSITION CLAIMS")

    output.execute("""
        INSERT INTO player_position_claims
        SELECT
            c.reep_id,
            c.label,
            c.provider,
            c.provider_namespace,
            c.provider_id,
            c.position,
            c.position_normalized,
            c.position_type,
            c.source_url,
            c.http_status,
            c.parser_version,
            c.retrieved_at
        FROM position.player_position_claims c
        INNER JOIN players p
            ON c.reep_id = p.reep_id
    """)

    position_claim_count = table_count(
        output,
        "player_position_claims"
    )

    print(
        f"Position claim rows: "
        f"{position_claim_count:,}"
    )

    # ============================================================
    # 8. PLAYER SEARCH INDEX
    # ============================================================

    header("8. BUILDING PLAYER SEARCH INDEX")

    output.execute("""
        INSERT INTO player_search
        SELECT
            p.reep_id,
            p.label,

            LOWER(
                TRIM(
                    COALESCE(p.label, '')
                    || ' '
                    || COALESCE(
                        (
                            SELECT STRING_AGG(
                                pa.alias,
                                ' '
                            )
                            FROM player_aliases pa
                            WHERE pa.reep_id = p.reep_id
                        ),
                        ''
                    )
                )
            ) AS search_text,

            (
                SELECT COUNT(*)
                FROM player_aliases pa
                WHERE pa.reep_id = p.reep_id
            ) AS alias_count,

            (
                SELECT COUNT(*)
                FROM player_external_ids pe
                WHERE pe.reep_id = p.reep_id
            ) AS external_id_count

        FROM players p
    """)

    search_count = table_count(
        output,
        "player_search"
    )

    print(
        f"Player search rows: "
        f"{search_count:,}"
    )

    # ============================================================
    # 9. DATABASE METADATA
    # ============================================================

    header("9. WRITING DATABASE METADATA")

    created_at = datetime.now(
        timezone.utc
    ).isoformat()

    metadata = {

        "schema_version":
            SCHEMA_VERSION,

        "source_database":
            str(SOURCE_DB),

        "position_database":
            str(POSITION_DB),

        "created_at":
            created_at,

        "player_count":
            str(players_count),

        "alias_count":
            str(aliases_count),

        "external_id_count":
            str(external_ids_count),

        "redirect_count":
            str(redirects_count),

        "club_evidence_count":
            str(club_count),

        "position_count":
            str(position_count),

        "position_claim_count":
            str(position_claim_count),

        "search_index_count":
            str(search_count),

        "position_provider":
            "transfermarkt",

        "position_parser_version":
            "TM-position-parser-v4",
    }

    for key, value in metadata.items():

        output.execute("""
            INSERT INTO database_metadata
            VALUES (?, ?)
        """, [
            key,
            value
        ])

    output.commit()

    # ============================================================
    # FINAL BUILD SUMMARY
    # ============================================================

    header("FINAL BUILD SUMMARY")

    tables = [
        "players",
        "player_aliases",
        "player_external_ids",
        "player_redirects",
        "player_club_evidence",
        "player_position",
        "player_position_claims",
        "player_search",
        "database_metadata",
    ]

    for table in tables:

        count = table_count(
            output,
            table
        )

        print(
            f"{table:<30} {count:>12,}"
        )

    print()
    print("Output database:")
    print(OUTPUT_DB)

    print()
    print("STATUS: BUILD COMPLETE")

    # ------------------------------------------------------------
    # Close database
    # ------------------------------------------------------------

    output.close()


if __name__ == "__main__":
    main()