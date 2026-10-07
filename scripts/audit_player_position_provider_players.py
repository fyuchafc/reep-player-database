"""
REEP PLAYER-ONLY POSITION PROVIDER AUDIT

READ-ONLY.

This audit corrects the previous bridge coverage audit by restricting
all provider counts to actual REEP player IDs from the players table.

No source database or v1.0.0 database is modified.
"""

from pathlib import Path
import duckdb
import json


ROOT = Path(__file__).resolve().parents[1]

SOURCE_DB = (
    Path(r"C:\Users\ADMIN\OneDrive\Documents\important database files")
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

OUTPUT = (
    ROOT
    / "output"
    / "reep-player-position-provider-player-only-audit.json"
)


TARGETS = [
    ("opta", "person"),
    ("wyscout", "player"),
    ("transfermarkt", "spieler"),
    ("fotmob", "person"),
    ("api_football", "player"),
    ("sportmonks", "player"),
    ("skillcorner", "player"),
    ("fifa", "person"),
    ("espn", "person"),
    ("eafc", "player"),
    ("fm", "player"),
    ("statsbomb", "offline_player"),
    ("uefa", "player"),
    ("fbref", "person"),
    ("worldfootball", "person_numeric"),
    ("besoccer", "player"),
    ("national_football_teams", "player"),
]


print("=" * 70)
print("REEP PLAYER-ONLY POSITION PROVIDER AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()

if not SOURCE_DB.exists():
    raise FileNotFoundError(SOURCE_DB)

con = duckdb.connect(
    str(SOURCE_DB),
    read_only=True
)

print("Connected successfully.")
print()


# ============================================================
# TOTAL PLAYER COUNT
# ============================================================

total_players = con.execute(
    """
    SELECT COUNT(*)
    FROM players
    """
).fetchone()[0]

print("=" * 70)
print("REEP PLAYER COUNT")
print("=" * 70)
print()
print(f"Total REEP players: {total_players:,}")
print()


# ============================================================
# VERIFY PLAYER IDs
# ============================================================

print("=" * 70)
print("PLAYER ID INTEGRITY")
print("=" * 70)

null_ids = con.execute(
    """
    SELECT COUNT(*)
    FROM players
    WHERE reep_id IS NULL
       OR TRIM(reep_id) = ''
    """
).fetchone()[0]

duplicate_ids = con.execute(
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

print(f"NULL/empty player IDs: {null_ids:,}")
print(f"Duplicate player IDs:  {duplicate_ids:,}")
print()


# ============================================================
# PROVIDER PLAYER-ONLY COVERAGE
# ============================================================

print("=" * 70)
print("PLAYER-ONLY PROVIDER COVERAGE")
print("=" * 70)

results = []

for provider, namespace in TARGETS:

    row = con.execute(
        """
        SELECT
            COUNT(*) AS bridge_rows,
            COUNT(DISTINCT b.reep_id) AS player_count
        FROM bridges b
        INNER JOIN players p
            ON p.reep_id = b.reep_id
        WHERE b.provider = ?
          AND b.namespace = ?
          AND b.external_id IS NOT NULL
          AND TRIM(b.external_id) <> ''
        """,
        [provider, namespace]
    ).fetchone()

    bridge_rows, player_count = row

    coverage = (
        player_count / total_players * 100
        if total_players
        else 0
    )

    print(
        f"{provider:<28}"
        f"{namespace:<22}"
        f"players={player_count:>8,} "
        f"coverage={coverage:>6.2f}% "
        f"rows={bridge_rows:>8,}"
    )

    results.append(
        {
            "provider": provider,
            "namespace": namespace,
            "bridge_rows": bridge_rows,
            "player_count": player_count,
            "coverage_percent": round(coverage, 4),
        }
    )

print()


# ============================================================
# UNIQUE PROVIDER ID COVERAGE
# ============================================================

print("=" * 70)
print("UNIQUE PROVIDER ID COVERAGE")
print("=" * 70)

unique_results = []

for provider, namespace in TARGETS:

    row = con.execute(
        """
        SELECT
            COUNT(DISTINCT b.external_id) AS unique_external_ids,
            COUNT(DISTINCT b.reep_id) AS player_count
        FROM bridges b
        INNER JOIN players p
            ON p.reep_id = b.reep_id
        WHERE b.provider = ?
          AND b.namespace = ?
          AND b.external_id IS NOT NULL
          AND TRIM(b.external_id) <> ''
        """,
        [provider, namespace]
    ).fetchone()

    unique_ids, player_count = row

    print(
        f"{provider:<28}"
        f"{namespace:<22}"
        f"unique IDs={unique_ids:>8,} "
        f"players={player_count:>8,}"
    )

    unique_results.append(
        {
            "provider": provider,
            "namespace": namespace,
            "unique_external_ids": unique_ids,
            "player_count": player_count,
        }
    )

print()


# ============================================================
# PROVIDER OVERLAP
# ============================================================

print("=" * 70)
print("POSITION PROVIDER OVERLAP")
print("=" * 70)

provider_names = [p for p, n in TARGETS]

for provider in provider_names:

    namespace = next(
        n for p, n in TARGETS
        if p == provider
    )

    count = con.execute(
        """
        SELECT COUNT(DISTINCT b.reep_id)
        FROM bridges b
        INNER JOIN players p
            ON p.reep_id = b.reep_id
        WHERE b.provider = ?
          AND b.namespace = ?
        """,
        [provider, namespace]
    ).fetchone()[0]

    print(
        f"{provider:<28} "
        f"{count:>8,} players"
    )

print()


# ============================================================
# ALL-PLAYER PROVIDER COUNTS
# ============================================================

print("=" * 70)
print("PLAYERS WITH AT LEAST ONE TARGET PROVIDER")
print("=" * 70)

provider_conditions = []

for provider, namespace in TARGETS:
    provider_conditions.append(
        f"""
        (
            b.provider = '{provider}'
            AND b.namespace = '{namespace}'
        )
        """
    )

where_clause = " OR ".join(provider_conditions)

target_player_count = con.execute(
    f"""
    SELECT COUNT(DISTINCT b.reep_id)
    FROM bridges b
    INNER JOIN players p
        ON p.reep_id = b.reep_id
    WHERE {where_clause}
    """
).fetchone()[0]

target_coverage = (
    target_player_count / total_players * 100
    if total_players
    else 0
)

print(
    f"Players with at least one target provider: "
    f"{target_player_count:,}"
)

print(
    f"Coverage: {target_coverage:.2f}%"
)

print()


# ============================================================
# PLAYERS WITH ZERO TARGET PROVIDERS
# ============================================================

zero_target = total_players - target_player_count

print(
    f"Players without a target provider: "
    f"{zero_target:,}"
)

print()


# ============================================================
# PROVIDER COUNT PER PLAYER
# ============================================================

print("=" * 70)
print("NUMBER OF TARGET POSITION PROVIDERS PER PLAYER")
print("=" * 70)

provider_count_distribution = con.execute(
    f"""
    SELECT
        provider_count,
        COUNT(*) AS players
    FROM (
        SELECT
            p.reep_id,
            COUNT(DISTINCT b.provider) AS provider_count
        FROM players p
        LEFT JOIN bridges b
            ON b.reep_id = p.reep_id
           AND ({where_clause})
        GROUP BY p.reep_id
    )
    GROUP BY provider_count
    ORDER BY provider_count
    """
).fetchall()

for provider_count, players in provider_count_distribution:

    print(
        f"{provider_count:>2} target providers: "
        f"{players:>8,} players"
    )

print()


# ============================================================
# BEST CANDIDATES
# ============================================================

print("=" * 70)
print("INITIAL POSITION-SOURCE CANDIDATES")
print("=" * 70)

sorted_results = sorted(
    results,
    key=lambda x: x["player_count"],
    reverse=True
)

for item in sorted_results:

    print(
        f"{item['provider']:<28}"
        f"{item['namespace']:<22}"
        f"{item['player_count']:>8,} "
        f"({item['coverage_percent']:.2f}%)"
    )

print()


# ============================================================
# SAVE REPORT
# ============================================================

report = {
    "source_database": str(SOURCE_DB),
    "read_only": True,
    "total_reep_players": total_players,
    "null_player_ids": null_ids,
    "duplicate_player_ids": duplicate_ids,
    "provider_results": results,
    "unique_provider_results": unique_results,
    "players_with_target_provider": target_player_count,
    "target_provider_coverage_percent": round(
        target_coverage,
        4
    ),
    "players_without_target_provider": zero_target,
    "provider_count_distribution": [
        {
            "target_provider_count": count,
            "players": players
        }
        for count, players in provider_count_distribution
    ],
}


with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(
        report,
        f,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# FINAL
# ============================================================

print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
print()
print(f"Report:")
print(OUTPUT)
print()
print("No source database changes were made.")
print("No v1.0.0 master changes were made.")
print()

con.close()