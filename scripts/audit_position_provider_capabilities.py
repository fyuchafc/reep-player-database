"""
REEP PLAYER DATABASE
POSITION PROVIDER CAPABILITY AUDIT

Purpose:
    Audit candidate football-data providers for position-data capability.

READ-ONLY:
    - Does NOT modify the REEP source database.
    - Does NOT modify the v1.0.0 master database.
    - Does NOT download player data.
    - Does NOT require API keys.

This is a documentation/capability audit based on the provider
identifiers already present in the REEP bridges table.

Output:
    output/reep-player-position-provider-capabilities.json
"""

from pathlib import Path
import json
import duckdb


# ============================================================
# PATHS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DB = (
    ROOT.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_JSON = OUTPUT_DIR / "reep-player-position-provider-capabilities.json"


# ============================================================
# CANDIDATE PROVIDERS
# ============================================================

PROVIDERS = [
    {
        "provider": "transfermarkt",
        "namespace": "spieler",
        "priority": 1,
        "coverage_percent": 89.47,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "WEB / THIRD-PARTY DATA ACCESS",
        "api_required": "NO_OFFICIAL_PUBLIC_API",
        "assessment": "STRONG_CANDIDATE",
        "notes": (
            "Very high REEP coverage. Transfermarkt player profiles "
            "contain position information and detailed position labels."
        ),
    },
    {
        "provider": "opta",
        "namespace": "person",
        "priority": 2,
        "coverage_percent": 89.08,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "COMMERCIAL DATA",
        "api_required": "COMMERCIAL_ACCESS",
        "assessment": "STRONG_BUT_ACCESS_LIMITED",
        "notes": (
            "Excellent REEP coverage. Opta provides detailed player "
            "position/role data, but access is commercial."
        ),
    },
    {
        "provider": "wyscout",
        "namespace": "player",
        "priority": 3,
        "coverage_percent": 77.32,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "COMMERCIAL API / PLATFORM",
        "api_required": "COMMERCIAL_ACCESS",
        "assessment": "EXCELLENT_DATA_BUT_ACCESS_LIMITED",
        "notes": (
            "Strong position model. Supports broad roles and detailed "
            "positions. Excellent candidate if legitimate API/platform "
            "access is available."
        ),
    },
    {
        "provider": "sportmonks",
        "namespace": "player",
        "priority": 4,
        "coverage_percent": 31.69,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "API",
        "api_required": "YES",
        "assessment": "STRONG_API_CANDIDATE",
        "notes": (
            "Player data exposes position and detailed position fields. "
            "Lower REEP coverage than the top providers but practical "
            "API-oriented structure."
        ),
    },
    {
        "provider": "api_football",
        "namespace": "player",
        "priority": 5,
        "coverage_percent": 35.77,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "API",
        "api_required": "YES",
        "assessment": "STRONG_API_CANDIDATE",
        "notes": (
            "Player statistics/profile data includes position information. "
            "Useful as an enrichment source."
        ),
    },
    {
        "provider": "fotmob",
        "namespace": "person",
        "priority": 6,
        "coverage_percent": 30.55,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "WEB / DATA ENDPOINTS",
        "api_required": "NO_OFFICIAL_PUBLIC_API",
        "assessment": "SECONDARY_CANDIDATE",
        "notes": (
            "Player pages and data commonly expose position information. "
            "Access/reproducibility must be evaluated before production use."
        ),
    },
    {
        "provider": "worldfootball",
        "namespace": "person_numeric",
        "priority": 7,
        "coverage_percent": 45.21,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "LIMITED",
        "access_type": "WEB",
        "api_required": "NO",
        "assessment": "SECONDARY_CANDIDATE",
        "notes": (
            "High coverage and useful historical player information. "
            "Position depth is less structured than dedicated APIs."
        ),
    },
    {
        "provider": "besoccer",
        "namespace": "player",
        "priority": 8,
        "coverage_percent": 42.38,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "WEB / DATA SERVICE",
        "api_required": "ACCESS_DEPENDENT",
        "assessment": "SECONDARY_CANDIDATE",
        "notes": (
            "Good coverage and player position information. "
            "Access and reproducibility require further validation."
        ),
    },
    {
        "provider": "fm",
        "namespace": "player",
        "priority": 9,
        "coverage_percent": 31.22,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "DATABASE / GAME DATA",
        "api_required": "ACCESS_DEPENDENT",
        "assessment": "SECONDARY_CANDIDATE",
        "notes": (
            "Football Manager data contains detailed playing-position "
            "information. Licensing/access needs verification."
        ),
    },
    {
        "provider": "fifa",
        "namespace": "person",
        "priority": 10,
        "coverage_percent": 22.95,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "LIMITED",
        "access_type": "OFFICIAL DATA",
        "api_required": "ACCESS_DEPENDENT",
        "assessment": "SECONDARY_CANDIDATE",
        "notes": (
            "Useful official football identity source, but lower REEP "
            "coverage and less attractive for complete position enrichment."
        ),
    },
    {
        "provider": "espn",
        "namespace": "person",
        "priority": 11,
        "coverage_percent": 21.90,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "WEB / DATA ENDPOINTS",
        "api_required": "ACCESS_DEPENDENT",
        "assessment": "SECONDARY_CANDIDATE",
        "notes": (
            "Player profiles generally expose position information."
        ),
    },
    {
        "provider": "eafc",
        "namespace": "player",
        "priority": 12,
        "coverage_percent": 17.52,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "GAME DATABASE",
        "api_required": "ACCESS_DEPENDENT",
        "assessment": "SECONDARY_CANDIDATE",
        "notes": (
            "EA FC player data contains detailed positions/roles, "
            "but coverage is comparatively low."
        ),
    },
    {
        "provider": "uefa",
        "namespace": "player",
        "priority": 13,
        "coverage_percent": 9.98,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "LIMITED",
        "access_type": "OFFICIAL DATA",
        "api_required": "ACCESS_DEPENDENT",
        "assessment": "SECONDARY_CANDIDATE",
        "notes": (
            "Official competition/player information. Lower REEP coverage."
        ),
    },
    {
        "provider": "statsbomb",
        "namespace": "offline_player",
        "priority": 14,
        "coverage_percent": 6.18,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "DATASET / API",
        "api_required": "ACCESS_DEPENDENT",
        "assessment": "SPECIALIST_SOURCE",
        "notes": (
            "Very strong analytical position/event data where available, "
            "but low REEP coverage."
        ),
    },
    {
        "provider": "fbref",
        "namespace": "person",
        "priority": 15,
        "coverage_percent": 3.70,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "YES",
        "access_type": "WEB",
        "api_required": "NO_OFFICIAL_PUBLIC_API",
        "assessment": "SECONDARY_VALIDATION_SOURCE",
        "notes": (
            "Excellent position information but very low REEP coverage."
        ),
    },
    {
        "provider": "national_football_teams",
        "namespace": "player",
        "priority": 16,
        "coverage_percent": 2.19,
        "position_capability": "YES",
        "broad_position": "YES",
        "detailed_position": "LIMITED",
        "access_type": "WEB",
        "api_required": "NO",
        "assessment": "SPECIALIST_SOURCE",
        "notes": (
            "Useful historical/national-team validation source but "
            "coverage is very low."
        ),
    },
]


# ============================================================
# DATABASE HELPERS
# ============================================================

def query_provider_stats(con, provider, namespace):
    query = """
        SELECT
            COUNT(DISTINCT b.reep_id) AS players,
            COUNT(*) AS rows,
            COUNT(DISTINCT b.external_id) AS unique_external_ids
        FROM bridges b
        INNER JOIN players p
            ON p.reep_id = b.reep_id
        WHERE LOWER(TRIM(b.provider)) = ?
          AND LOWER(TRIM(b.namespace)) = ?
    """

    row = con.execute(query, [provider, namespace]).fetchone()

    return {
        "players": int(row[0] or 0),
        "rows": int(row[1] or 0),
        "unique_external_ids": int(row[2] or 0),
    }


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("REEP PLAYER POSITION PROVIDER CAPABILITY AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()

if not SOURCE_DB.exists():
    print("ERROR: Source database not found:")
    print(SOURCE_DB)
    raise SystemExit(1)

con = duckdb.connect(str(SOURCE_DB), read_only=True)

print("Connected successfully.")
print()

# ------------------------------------------------------------
# Player count
# ------------------------------------------------------------

total_players = con.execute(
    "SELECT COUNT(*) FROM players"
).fetchone()[0]

print("=" * 70)
print("REEP PLAYER COUNT")
print("=" * 70)
print()
print(f"Total REEP players: {total_players:,}")
print()

# ------------------------------------------------------------
# Provider statistics
# ------------------------------------------------------------

print("=" * 70)
print("PROVIDER CAPABILITY REVIEW")
print("=" * 70)
print()

results = []

for item in PROVIDERS:
    stats = query_provider_stats(
        con,
        item["provider"],
        item["namespace"],
    )

    coverage = (
        stats["players"] / total_players * 100
        if total_players
        else 0
    )

    result = dict(item)

    result["actual_players"] = stats["players"]
    result["actual_rows"] = stats["rows"]
    result["actual_unique_external_ids"] = stats["unique_external_ids"]
    result["actual_coverage_percent"] = round(coverage, 2)

    results.append(result)

    print(
        f"{item['provider']:28}"
        f"{item['namespace']:22}"
        f"players={stats['players']:>8,} "
        f"coverage={coverage:>6.2f}% "
        f"assessment={item['assessment']}"
    )

print()

# ------------------------------------------------------------
# Best candidates
# ------------------------------------------------------------

print("=" * 70)
print("POSITION PROVIDER RECOMMENDATION TIERS")
print("=" * 70)
print()

tiers = {
    "PRIMARY_CANDIDATES": [
        "transfermarkt",
        "opta",
        "wyscout",
    ],
    "API_CANDIDATES": [
        "sportmonks",
        "api_football",
    ],
    "SECONDARY_CANDIDATES": [
        "fotmob",
        "worldfootball",
        "besoccer",
        "fm",
        "fifa",
        "espn",
        "eafc",
        "uefa",
    ],
    "SPECIALIST_OR_VALIDATION": [
        "statsbomb",
        "fbref",
        "national_football_teams",
    ],
}

for tier_name, providers in tiers.items():
    print(tier_name)
    for provider in providers:
        matches = [
            x for x in results
            if x["provider"] == provider
        ]

        if matches:
            x = matches[0]
            print(
                f"  {provider:28}"
                f"{x['actual_players']:>8,} players "
                f"{x['actual_coverage_percent']:>6.2f}%"
            )
    print()

# ------------------------------------------------------------
# Coverage checks
# ------------------------------------------------------------

invalid_coverage = [
    x for x in results
    if x["actual_coverage_percent"] > 100
]

if invalid_coverage:
    print("=" * 70)
    print("COVERAGE VALIDATION")
    print("=" * 70)
    print()
    print("FAIL")
    print()
    for x in invalid_coverage:
        print(
            f"{x['provider']} / {x['namespace']} "
            f"reported {x['actual_coverage_percent']}%"
        )
    print()
    raise SystemExit(1)

print("=" * 70)
print("COVERAGE VALIDATION")
print("=" * 70)
print()
print("PASS")
print("All provider coverage values are within 0–100%.")
print()

# ------------------------------------------------------------
# Output
# ------------------------------------------------------------

report = {
    "audit": "REEP Player Position Provider Capability Audit",
    "read_only": True,
    "source_database": str(SOURCE_DB),
    "total_reep_players": int(total_players),
    "providers": results,
    "recommendation": {
        "primary": [
            "transfermarkt",
            "opta",
            "wyscout",
        ],
        "api_candidates": [
            "sportmonks",
            "api_football",
        ],
        "secondary": [
            "fotmob",
            "worldfootball",
            "besoccer",
            "fm",
            "fifa",
            "espn",
            "eafc",
            "uefa",
        ],
        "specialist_validation": [
            "statsbomb",
            "fbref",
            "national_football_teams",
        ],
    },
    "validation": {
        "coverage_values_valid": len(invalid_coverage) == 0,
        "source_modified": False,
        "v1_master_modified": False,
    },
}

OUTPUT_JSON.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

con.close()

print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
print()
print("Report:")
print(OUTPUT_JSON)
print()
print("No source database changes were made.")
print("No v1.0.0 master changes were made.")
print()