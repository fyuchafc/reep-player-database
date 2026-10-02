import csv
import json
import os
import sys
from collections import Counter

import duckdb


# ============================================================
# REEP PLAYER CLUB / CAREER EVIDENCE AUDIT
# ============================================================
#
# READ-ONLY AUDIT
#
# Purpose:
#   Determine exactly what REEP exposes about player club
#   observations, seasons, matches, teams, and career evidence.
#
# IMPORTANT:
#   observed_clubs is explicitly NOT a complete career history.
#   This audit therefore does NOT reconstruct careers.
#
# This script does NOT:
#   - modify the source database
#   - merge players
#   - delete players
#   - invent club histories
#   - infer missing transfers
#   - infer player appearances from match/team relationships
#
# ============================================================


SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = "output"

JSON_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "reep-player-club-evidence-audit.json"
)

CSV_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "reep-player-club-evidence.csv"
)


def safe(value):
    if value is None:
        return None
    return str(value)


def main():

    print("=" * 70)
    print("REEP PLAYER CLUB / CAREER EVIDENCE AUDIT")
    print("=" * 70)
    print()
    print("READ-ONLY — source database will NOT be modified.")
    print()
    print(
        "IMPORTANT: This audit measures available evidence."
    )
    print(
        "It does NOT reconstruct complete player careers."
    )
    print()

    if not os.path.exists(SOURCE_DB):
        print("ERROR: Source database not found:")
        print(SOURCE_DB)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    file_size = os.path.getsize(SOURCE_DB)

    print("SOURCE DATABASE")
    print("-" * 70)
    print(SOURCE_DB)
    print(
        f"File size: {file_size:,} bytes "
        f"({file_size / (1024 * 1024):.2f} MiB)"
    )
    print()

    print("OPENING DATABASE READ-ONLY...")
    print()

    con = duckdb.connect(
        SOURCE_DB,
        read_only=True
    )

    # --------------------------------------------------------
    # Verify required tables
    # --------------------------------------------------------

    print("VERIFYING REQUIRED TABLES...")
    print()

    required_tables = [
        "main.players",
        "main.observed_clubs",
        "main.matches",
        "main.teams",
        "main.seasons",
        "main.stages",
        "main.relationships",
    ]

    available_tables = {
        row[0]
        for row in con.execute(
            """
            SELECT table_schema || '.' || table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
        ).fetchall()
    }

    for table in required_tables:
        if table not in available_tables:
            print(f"ERROR: Required table missing: {table}")
            con.close()
            sys.exit(1)

    print("Required tables found.")
    print()

    # --------------------------------------------------------
    # Table row counts
    # --------------------------------------------------------

    print("READING TABLE COUNTS...")
    print()

    table_counts = {}

    for table in required_tables:

        count = con.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        table_counts[table] = count

        print(
            f"{table}: {count:,}"
        )

    print()

    # --------------------------------------------------------
    # Observed clubs
    # --------------------------------------------------------

    print("LOADING OBSERVED CLUB EVIDENCE...")
    print()

    observed_rows = con.execute(
        """
        SELECT
            o.reep_id,
            p.label,
            p.status,
            p.gender,
            o.entity_type,
            o.observed_clubs,
            o.first_observed_season,
            o.last_observed_season,
            o.basis
        FROM main.observed_clubs o
        INNER JOIN main.players p
            ON p.reep_id = o.reep_id
        ORDER BY
            o.observed_clubs DESC,
            o.reep_id
        """
    ).fetchall()

    print(
        f"Player observed-club rows: "
        f"{len(observed_rows):,}"
    )
    print()

    # --------------------------------------------------------
    # Observed-club distributions
    # --------------------------------------------------------

    observed_count_distribution = Counter(
        row[5]
        for row in observed_rows
    )

    first_season_distribution = Counter(
        safe(row[6])
        for row in observed_rows
    )

    last_season_distribution = Counter(
        safe(row[7])
        for row in observed_rows
    )

    basis_distribution = Counter(
        safe(row[8])
        for row in observed_rows
    )

    entity_type_distribution = Counter(
        safe(row[4])
        for row in observed_rows
    )

    players_with_observed_clubs = {
        row[0]
        for row in observed_rows
    }

    # --------------------------------------------------------
    # Verify observed-club basis text
    # --------------------------------------------------------

    basis_values = sorted(
        {
            safe(row[8])
            for row in observed_rows
        }
    )

    # --------------------------------------------------------
    # Players without observed-club rows
    # --------------------------------------------------------

    total_players = con.execute(
        """
        SELECT COUNT(*)
        FROM main.players
        """
    ).fetchone()[0]

    players_without_observed_clubs = (
        total_players
        - len(players_with_observed_clubs)
    )

    # --------------------------------------------------------
    # Seasons
    # --------------------------------------------------------

    print("ANALYZING SEASONS...")
    print()

    season_count = con.execute(
        """
        SELECT COUNT(*)
        FROM main.seasons
        """
    ).fetchone()[0]

    distinct_season_labels = con.execute(
        """
        SELECT COUNT(DISTINCT label)
        FROM main.seasons
        WHERE label IS NOT NULL
        """
    ).fetchone()[0]

    # --------------------------------------------------------
    # Teams
    # --------------------------------------------------------

    print("ANALYZING TEAMS...")
    print()

    team_count = con.execute(
        """
        SELECT COUNT(*)
        FROM main.teams
        """
    ).fetchone()[0]

    team_with_labels = con.execute(
        """
        SELECT COUNT(*)
        FROM main.teams
        WHERE label IS NOT NULL
        """
    ).fetchone()[0]

    # --------------------------------------------------------
    # Match player linkage test
    # --------------------------------------------------------

    print("TESTING FOR DIRECT PLAYER-MATCH LINKS...")
    print()

    player_relationship_rows = con.execute(
        """
        SELECT COUNT(*)
        FROM main.relationships r
        INNER JOIN main.players p1
            ON p1.reep_id = r.from_id
        """
    ).fetchone()[0]

    player_relationship_rows_reverse = con.execute(
        """
        SELECT COUNT(*)
        FROM main.relationships r
        INNER JOIN main.players p2
            ON p2.reep_id = r.to_id
        """
    ).fetchone()[0]

    # --------------------------------------------------------
    # Relationship kinds involving players
    # --------------------------------------------------------

    player_relationship_kinds = con.execute(
        """
        SELECT
            r.kind,
            COUNT(*)
        FROM main.relationships r
        WHERE r.from_id IN (
            SELECT reep_id
            FROM main.players
        )
        OR r.to_id IN (
            SELECT reep_id
            FROM main.players
        )
        GROUP BY r.kind
        ORDER BY COUNT(*) DESC
        """
    ).fetchall()

    # --------------------------------------------------------
    # Match table structure
    # --------------------------------------------------------

    match_columns = con.execute(
        """
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'main'
          AND table_name = 'matches'
        ORDER BY ordinal_position
        """
    ).fetchall()

    # --------------------------------------------------------
    # Observed-club examples
    # --------------------------------------------------------

    examples = []

    for row in observed_rows[:25]:

        examples.append(
            {
                "reep_id": row[0],
                "label": safe(row[1]),
                "status": safe(row[2]),
                "gender": safe(row[3]),
                "entity_type": safe(row[4]),
                "observed_clubs": row[5],
                "first_observed_season": safe(row[6]),
                "last_observed_season": safe(row[7]),
                "basis": safe(row[8]),
            }
        )

    # --------------------------------------------------------
    # Highest observed-club counts
    # --------------------------------------------------------

    highest_observed_clubs = []

    for row in observed_rows[:100]:

        highest_observed_clubs.append(
            {
                "reep_id": row[0],
                "label": safe(row[1]),
                "status": safe(row[2]),
                "gender": safe(row[3]),
                "observed_clubs": row[5],
                "first_observed_season": safe(row[6]),
                "last_observed_season": safe(row[7]),
                "basis": safe(row[8]),
            }
        )

    # --------------------------------------------------------
    # Players with season span
    # --------------------------------------------------------

    season_span_rows = []

    for row in observed_rows:

        first = row[6]
        last = row[7]

        if first is not None and last is not None:

            season_span_rows.append(
                {
                    "reep_id": row[0],
                    "label": safe(row[1]),
                    "first_observed_season": safe(first),
                    "last_observed_season": safe(last),
                    "observed_clubs": row[5],
                }
            )

    # --------------------------------------------------------
    # Inspect whether observed clubs has actual club IDs
    # --------------------------------------------------------

    observed_columns = con.execute(
        """
        SELECT
            column_name,
            data_type
        FROM information_schema.columns
        WHERE table_schema = 'main'
          AND table_name = 'observed_clubs'
        ORDER BY ordinal_position
        """
    ).fetchall()

    # --------------------------------------------------------
    # Inspect relationships involving team/player IDs
    # --------------------------------------------------------

    relationship_kind_map = {
        safe(row[0]): row[1]
        for row in player_relationship_kinds
    }

    # --------------------------------------------------------
    # Build audit JSON
    # --------------------------------------------------------

    audit = {
        "audit": {
            "name": "REEP Player Club / Career Evidence Audit",
            "read_only": True,
            "source_database": SOURCE_DB,
            "source_file_size_bytes": file_size,
            "career_reconstruction": False,
        },

        "table_counts": table_counts,

        "players": {
            "total_players": total_players,
            "players_with_observed_club_rows": len(
                players_with_observed_clubs
            ),
            "players_without_observed_club_rows": (
                players_without_observed_clubs
            ),
        },

        "observed_clubs": {
            "player_rows": len(observed_rows),
            "entity_type_distribution": dict(
                entity_type_distribution
            ),
            "observed_club_count_distribution": {
                safe(key): value
                for key, value
                in sorted(
                    observed_count_distribution.items(),
                    key=lambda item: (
                        -1
                        if item[0] is None
                        else item[0]
                    )
                )
            },
            "first_observed_season_values": dict(
                first_season_distribution
            ),
            "last_observed_season_values": dict(
                last_season_distribution
            ),
            "basis_distribution": dict(
                basis_distribution
            ),
            "basis_values": basis_values,
            "columns": [
                {
                    "column_name": row[0],
                    "data_type": row[1],
                }
                for row in observed_columns
            ],
        },

        "seasons": {
            "rows": season_count,
            "distinct_non_null_labels": (
                distinct_season_labels
            ),
        },

        "teams": {
            "rows": team_count,
            "rows_with_labels": team_with_labels,
        },

        "matches": {
            "columns": [
                {
                    "column_name": row[0],
                    "data_type": row[1],
                }
                for row in match_columns
            ],
        },

        "player_relationship_test": {
            "relationships_with_player_as_from_id": (
                player_relationship_rows
            ),
            "relationships_with_player_as_to_id": (
                player_relationship_rows_reverse
            ),
            "relationship_kinds_involving_players": (
                relationship_kind_map
            ),
        },

        "examples": examples,

        "highest_observed_club_counts": (
            highest_observed_clubs
        ),

        "players_with_observed_season_span": (
            season_span_rows[:100]
        ),
    }

    # --------------------------------------------------------
    # Write JSON
    # --------------------------------------------------------

    with open(
        JSON_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            audit,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Write CSV
    # --------------------------------------------------------

    with open(
        CSV_OUTPUT,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            [
                "reep_id",
                "label",
                "status",
                "gender",
                "entity_type",
                "observed_clubs",
                "first_observed_season",
                "last_observed_season",
                "basis",
            ]
        )

        for row in observed_rows:

            writer.writerow(
                [
                    row[0],
                    safe(row[1]),
                    safe(row[2]),
                    safe(row[3]),
                    safe(row[4]),
                    row[5],
                    safe(row[6]),
                    safe(row[7]),
                    safe(row[8]),
                ]
            )

    # --------------------------------------------------------
    # Console report
    # --------------------------------------------------------

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    print(
        f"Total REEP players:                    "
        f"{total_players:,}"
    )

    print(
        f"Players with observed-club rows:       "
        f"{len(players_with_observed_clubs):,}"
    )

    print(
        f"Players without observed-club rows:    "
        f"{players_without_observed_clubs:,}"
    )

    print()

    print(
        f"Player observed-club rows:             "
        f"{len(observed_rows):,}"
    )

    print(
        f"Season rows:                            "
        f"{season_count:,}"
    )

    print(
        f"Distinct season labels:                "
        f"{distinct_season_labels:,}"
    )

    print(
        f"Team rows:                              "
        f"{team_count:,}"
    )

    print(
        f"Teams with labels:                     "
        f"{team_with_labels:,}"
    )

    print()

    print("=" * 70)
    print("OBSERVED CLUB COUNT DISTRIBUTION")
    print("=" * 70)

    for count, number in sorted(
        observed_count_distribution.items(),
        key=lambda item: (
            item[0] is None,
            item[0] if item[0] is not None else -1
        )
    ):

        print(
            f"{count}: {number:,}"
        )

    print()

    print("=" * 70)
    print("OBSERVED CLUB BASIS")
    print("=" * 70)

    for basis, number in basis_distribution.items():

        print(
            f"{basis}: {number:,}"
        )

    print()

    print("=" * 70)
    print("DIRECT PLAYER-RELATIONSHIP TEST")
    print("=" * 70)

    print(
        "Relationships with player as from_id: "
        f"{player_relationship_rows:,}"
    )

    print(
        "Relationships with player as to_id:   "
        f"{player_relationship_rows_reverse:,}"
    )

    if player_relationship_kinds:

        print()
        print("Relationship kinds involving players:")

        for kind, count in player_relationship_kinds:

            print(
                f"  {kind}: {count:,}"
            )

    else:

        print()
        print(
            "No relationships directly reference "
            "players."
        )

    print()

    print("=" * 70)
    print("OBSERVED CLUB TABLE COLUMNS")
    print("=" * 70)

    for column_name, data_type in observed_columns:

        print(
            f"{column_name}: {data_type}"
        )

    print()

    print("=" * 70)
    print("MATCH TABLE COLUMNS")
    print("=" * 70)

    for column_name, data_type in match_columns:

        print(
            f"{column_name}: {data_type}"
        )

    print()

    print("=" * 70)
    print("HIGHEST OBSERVED CLUB COUNTS")
    print("=" * 70)

    for item in highest_observed_clubs[:20]:

        print(
            f"{item['reep_id']} | "
            f"{item['label']} | "
            f"clubs={item['observed_clubs']} | "
            f"first={item['first_observed_season']} | "
            f"last={item['last_observed_season']}"
        )

    print()

    print("=" * 70)
    print("OUTPUT FILES")
    print("=" * 70)

    print(JSON_OUTPUT)
    print(CSV_OUTPUT)

    print()

    print("AUDIT COMPLETE")
    print("Source database was opened READ-ONLY.")
    print("No player records were modified.")
    print("No career history was reconstructed.")
    print("No club history was invented.")

    con.close()


if __name__ == "__main__":
    main()