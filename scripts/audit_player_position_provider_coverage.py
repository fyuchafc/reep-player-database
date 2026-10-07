"""
REEP PLAYER POSITION PROVIDER COVERAGE AUDIT

READ-ONLY.

Purpose:
Identify external provider IDs available for REEP players
that may be useful for position enrichment.

The source REEP database and v1.0.0 master are NOT modified.
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

OUTPUT = ROOT / "output" / "reep-player-position-provider-coverage.json"


print("=" * 70)
print("REEP PLAYER POSITION PROVIDER COVERAGE AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()
print("Source:")
print(SOURCE_DB)
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
# TOTAL PLAYERS
# ============================================================

total_players = con.execute(
    """
    SELECT COUNT(*)
    FROM players
    """
).fetchone()[0]

print("=" * 70)
print("TOTAL REEP PLAYERS")
print("=" * 70)

print(f"Total REEP players: {total_players:,}")
print()


# ============================================================
# PROVIDER COVERAGE
# ============================================================

print("=" * 70)
print("POSITION-CANDIDATE PROVIDER COVERAGE")
print("=" * 70)

rows = con.execute(
    """
    SELECT
        provider,
        namespace,
        COUNT(*) AS bridge_rows,
        COUNT(DISTINCT reep_id) AS player_count
    FROM bridges
    WHERE reep_id IS NOT NULL
      AND TRIM(reep_id) <> ''
    GROUP BY provider, namespace
    ORDER BY player_count DESC, provider, namespace
    """
).fetchall()


results = []

for provider, namespace, bridge_rows, player_count in rows:

    coverage = (
        player_count / total_players * 100
        if total_players
        else 0
    )

    print(
        f"{provider:<30} "
        f"{namespace:<25} "
        f"players={player_count:>8,} "
        f"coverage={coverage:>6.2f}% "
        f"rows={bridge_rows:>9,}"
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
# PROVIDER-LEVEL COLLAPSED COVERAGE
# ============================================================

print("=" * 70)
print("PROVIDER-LEVEL PLAYER COVERAGE")
print("=" * 70)

provider_rows = con.execute(
    """
    SELECT
        provider,
        COUNT(DISTINCT reep_id) AS player_count,
        COUNT(*) AS bridge_rows,
        COUNT(DISTINCT namespace) AS namespaces
    FROM bridges
    WHERE reep_id IS NOT NULL
      AND TRIM(reep_id) <> ''
    GROUP BY provider
    ORDER BY player_count DESC, provider
    """
).fetchall()


provider_results = []

for provider, player_count, bridge_rows, namespaces in provider_rows:

    coverage = (
        player_count / total_players * 100
        if total_players
        else 0
    )

    print(
        f"{provider:<30} "
        f"players={player_count:>8,} "
        f"coverage={coverage:>6.2f}% "
        f"namespaces={namespaces:>3} "
        f"rows={bridge_rows:>9,}"
    )

    provider_results.append(
        {
            "provider": provider,
            "player_count": player_count,
            "coverage_percent": round(coverage, 4),
            "namespaces": namespaces,
            "bridge_rows": bridge_rows,
        }
    )

print()


# ============================================================
# KEY POSITION PROVIDERS
# ============================================================

target_providers = [
    "opta",
    "wyscout",
    "transfermarkt",
    "fotmob",
    "api_football",
    "sportmonks",
    "fifa",
    "espn",
    "eafc",
    "fm",
    "skillcorner",
    "statsbomb",
    "uefa",
    "fbref",
    "sofascore",
    "soccerway",
    "worldfootball",
]


print("=" * 70)
print("KEY POSITION PROVIDER SUMMARY")
print("=" * 70)

key_results = []

for provider in target_providers:

    match = next(
        (
            item
            for item in provider_results
            if item["provider"] == provider
        ),
        None
    )

    if match:

        print(
            f"{provider:<20} "
            f"{match['player_count']:>8,} players "
            f"({match['coverage_percent']:.2f}%)"
        )

        key_results.append(match)

    else:

        print(
            f"{provider:<20} "
            f"NO REEP PLAYER COVERAGE"
        )


print()


# ============================================================
# MULTI-PROVIDER COVERAGE
# ============================================================

print("=" * 70)
print("MULTI-PROVIDER COVERAGE")
print("=" * 70)

multi_rows = con.execute(
    """
    SELECT
        reep_id,
        COUNT(DISTINCT provider) AS provider_count
    FROM bridges
    WHERE reep_id IS NOT NULL
      AND TRIM(reep_id) <> ''
    GROUP BY reep_id
    """
).fetchall()

distribution = {}

for reep_id, provider_count in multi_rows:
    distribution[provider_count] = (
        distribution.get(provider_count, 0) + 1
    )

for count in sorted(distribution):
    print(
        f"{count:>3} providers: "
        f"{distribution[count]:>8,} players"
    )

print()


# ============================================================
# TOP POSITION-CANDIDATE NAMESPACE COVERAGE
# ============================================================

print("=" * 70)
print("IMPORTANT PLAYER NAMESPACES")
print("=" * 70)

important_namespaces = [
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
]


namespace_results = []

for provider, namespace in important_namespaces:

    row = con.execute(
        """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT reep_id) AS players
        FROM bridges
        WHERE provider = ?
          AND namespace = ?
          AND reep_id IS NOT NULL
          AND TRIM(reep_id) <> ''
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
        f"{provider:<20} "
        f"{namespace:<20} "
        f"players={player_count:>8,} "
        f"coverage={coverage:>6.2f}%"
    )

    namespace_results.append(
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
# SAVE REPORT
# ============================================================

report = {
    "source_database": str(SOURCE_DB),
    "read_only": True,
    "total_reep_players": total_players,
    "provider_namespace_coverage": results,
    "provider_coverage": provider_results,
    "key_position_providers": key_results,
    "provider_count_distribution": distribution,
    "important_namespaces": namespace_results,
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