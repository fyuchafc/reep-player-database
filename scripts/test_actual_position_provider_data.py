"""
REEP PLAYER DATABASE
ACTUAL POSITION PROVIDER DATA TEST

PURPOSE
-------
Tests whether provider IDs already stored in the REEP database can
be resolved to actual player profile/position information.

IMPORTANT
---------
READ-ONLY.

This script:
    - NEVER modifies the REEP source database.
    - NEVER modifies the v1.0.0 master database.
    - NEVER writes into any DuckDB database.
    - Does NOT require API keys.
    - Does NOT attempt large-scale scraping.
    - Uses only a small controlled sample.
    - Records provider IDs and accessibility results.

The first phase deliberately tests only public HTTP accessibility.

Providers tested:
    - Transfermarkt
    - Wyscout
    - Opta
    - API-Football
    - Sportmonks

The script does NOT assume that an HTTP failure means the provider
does not contain position data. Authentication, anti-bot protection,
or subscription requirements can cause failure.

Output:
    output/reep-actual-position-provider-test.json
    output/reep-actual-position-provider-test.csv
"""

from pathlib import Path
import csv
import json
import re
import time
import urllib.error
import urllib.request

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

OUTPUT_JSON = OUTPUT_DIR / "reep-actual-position-provider-test.json"
OUTPUT_CSV = OUTPUT_DIR / "reep-actual-position-provider-test.csv"


# ============================================================
# TEST SETTINGS
# ============================================================

# Small sample only.
# This is deliberately NOT a bulk retrieval job.
SAMPLE_SIZE = 10

# HTTP timeout.
TIMEOUT_SECONDS = 15

# Delay between public requests.
REQUEST_DELAY_SECONDS = 2


# ============================================================
# PROVIDER URL BUILDERS
# ============================================================

def build_url(provider, namespace, external_id):
    """
    Build a public profile URL where a reasonably predictable URL
    pattern exists.

    IMPORTANT:
    These URLs are TEST URLs only.

    A failed request does NOT prove that the provider lacks position
    data. It may simply mean authentication, anti-bot protection,
    changed URL structure, or another access restriction.
    """

    external_id = str(external_id).strip()

    if provider == "transfermarkt":
        # Transfermarkt player profile URL commonly uses:
        # /spieler/profil/spieler/<ID>
        return (
            "https://www.transfermarkt.com/"
            f"-/profil/spieler/{external_id}"
        )

    if provider == "wyscout":
        # Wyscout's documented API endpoint is authenticated.
        # We intentionally do NOT call it without credentials.
        return None

    if provider == "opta":
        # Opta player data is commercial.
        # No anonymous public endpoint is assumed.
        return None

    if provider == "api_football":
        # API-Football requires an API key.
        # We intentionally do NOT call it without credentials.
        return None

    if provider == "sportmonks":
        # Sportmonks API requires authentication.
        # We intentionally do NOT call it without credentials.
        return None

    return None


# ============================================================
# HTTP TEST
# ============================================================

def test_public_url(url):
    """
    Test whether a public URL can be reached.

    Returns a structured result.

    We do not parse or store the complete webpage.
    """

    if not url:
        return {
            "attempted": False,
            "http_status": None,
            "accessible": False,
            "reason": "NO_PUBLIC_ENDPOINT_TESTED",
            "content_type": None,
            "position_found": False,
            "position_values": [],
        }

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/154.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
        ) as response:

            status = response.status
            content_type = response.headers.get(
                "Content-Type",
                "",
            )

            # Read only a limited amount.
            # This is a capability test, NOT a scraper.
            body = response.read(200_000)

            text = body.decode(
                "utf-8",
                errors="ignore",
            )

            # Very conservative position keyword search.
            # We DO NOT treat these as confirmed position evidence.
            candidates = []

            patterns = [
                r"\bGoalkeeper\b",
                r"\bDefender\b",
                r"\bMidfielder\b",
                r"\bForward\b",
                r"\bCentre-Back\b",
                r"\bCenter-Back\b",
                r"\bLeft-Back\b",
                r"\bRight-Back\b",
                r"\bDefensive Midfield\b",
                r"\bCentral Midfield\b",
                r"\bAttacking Midfield\b",
                r"\bLeft Winger\b",
                r"\bRight Winger\b",
                r"\bStriker\b",
            ]

            for pattern in patterns:
                if re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                ):
                    candidates.append(
                        re.sub(
                            r"\\b",
                            "",
                            pattern,
                        )
                    )

            return {
                "attempted": True,
                "http_status": status,
                "accessible": status == 200,
                "reason": (
                    "HTTP_200"
                    if status == 200
                    else f"HTTP_{status}"
                ),
                "content_type": content_type,
                "position_found": bool(candidates),
                "position_values": sorted(
                    set(candidates)
                ),
            }

    except urllib.error.HTTPError as exc:
        return {
            "attempted": True,
            "http_status": exc.code,
            "accessible": False,
            "reason": f"HTTP_{exc.code}",
            "content_type": None,
            "position_found": False,
            "position_values": [],
        }

    except urllib.error.URLError as exc:
        return {
            "attempted": True,
            "http_status": None,
            "accessible": False,
            "reason": f"URL_ERROR: {exc.reason}",
            "content_type": None,
            "position_found": False,
            "position_values": [],
        }

    except Exception as exc:
        return {
            "attempted": True,
            "http_status": None,
            "accessible": False,
            "reason": f"ERROR: {type(exc).__name__}: {exc}",
            "content_type": None,
            "position_found": False,
            "position_values": [],
        }


# ============================================================
# DATABASE SAMPLE
# ============================================================

def get_sample_players(con):
    """
    Select actual REEP players with provider IDs.

    We deliberately select players who have several of the target
    providers so that the same real player can eventually be compared
    across providers.
    """

    query = """
        WITH provider_flags AS (
            SELECT
                p.reep_id,
                p.label,
                p.gender,
                MAX(
                    CASE
                        WHEN LOWER(TRIM(b.provider)) = 'transfermarkt'
                         AND LOWER(TRIM(b.namespace)) = 'spieler'
                        THEN b.external_id
                    END
                ) AS transfermarkt_id,
                MAX(
                    CASE
                        WHEN LOWER(TRIM(b.provider)) = 'wyscout'
                         AND LOWER(TRIM(b.namespace)) = 'player'
                        THEN b.external_id
                    END
                ) AS wyscout_id,
                MAX(
                    CASE
                        WHEN LOWER(TRIM(b.provider)) = 'opta'
                         AND LOWER(TRIM(b.namespace)) = 'person'
                        THEN b.external_id
                    END
                ) AS opta_id,
                MAX(
                    CASE
                        WHEN LOWER(TRIM(b.provider)) = 'api_football'
                         AND LOWER(TRIM(b.namespace)) = 'player'
                        THEN b.external_id
                    END
                ) AS api_football_id,
                MAX(
                    CASE
                        WHEN LOWER(TRIM(b.provider)) = 'sportmonks'
                         AND LOWER(TRIM(b.namespace)) = 'player'
                        THEN b.external_id
                    END
                ) AS sportmonks_id
            FROM players p
            LEFT JOIN bridges b
                ON b.reep_id = p.reep_id
            GROUP BY
                p.reep_id,
                p.label,
                p.gender
        )
        SELECT
            reep_id,
            label,
            gender,
            transfermarkt_id,
            wyscout_id,
            opta_id,
            api_football_id,
            sportmonks_id
        FROM provider_flags
        WHERE
            transfermarkt_id IS NOT NULL
            OR wyscout_id IS NOT NULL
            OR opta_id IS NOT NULL
            OR api_football_id IS NOT NULL
            OR sportmonks_id IS NOT NULL
        ORDER BY
            (
                CASE WHEN transfermarkt_id IS NOT NULL THEN 1 ELSE 0 END
                +
                CASE WHEN wyscout_id IS NOT NULL THEN 1 ELSE 0 END
                +
                CASE WHEN opta_id IS NOT NULL THEN 1 ELSE 0 END
                +
                CASE WHEN api_football_id IS NOT NULL THEN 1 ELSE 0 END
                +
                CASE WHEN sportmonks_id IS NOT NULL THEN 1 ELSE 0 END
            ) DESC,
            reep_id
        LIMIT ?
    """

    rows = con.execute(
        query,
        [SAMPLE_SIZE],
    ).fetchall()

    columns = [
        "reep_id",
        "label",
        "gender",
        "transfermarkt_id",
        "wyscout_id",
        "opta_id",
        "api_football_id",
        "sportmonks_id",
    ]

    return [
        dict(zip(columns, row))
        for row in rows
    ]


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("REEP ACTUAL POSITION PROVIDER DATA TEST")
print("=" * 70)
print()
print("READ-ONLY — no database will be modified.")
print()
print(f"Sample size: {SAMPLE_SIZE} players")
print()

if not SOURCE_DB.exists():
    print("ERROR: Source database not found:")
    print(SOURCE_DB)
    raise SystemExit(1)

con = duckdb.connect(
    str(SOURCE_DB),
    read_only=True,
)

print("Source database connected successfully.")
print()

# ------------------------------------------------------------
# Source player count
# ------------------------------------------------------------

total_players = con.execute(
    "SELECT COUNT(*) FROM players"
).fetchone()[0]

print(f"Total REEP players: {total_players:,}")
print()

# ------------------------------------------------------------
# Sample
# ------------------------------------------------------------

sample = get_sample_players(con)

if not sample:
    print("FAIL: No players with provider IDs were found.")
    con.close()
    raise SystemExit(1)

print("=" * 70)
print("TEST SAMPLE")
print("=" * 70)
print()

for index, player in enumerate(sample, start=1):
    print(
        f"{index:02d}. "
        f"{player['reep_id']} | "
        f"{player['label']}"
    )

print()

# ------------------------------------------------------------
# Provider testing
# ------------------------------------------------------------

results = []

for player in sample:

    print("-" * 70)
    print(
        f"PLAYER: {player['label']} "
        f"({player['reep_id']})"
    )
    print("-" * 70)

    provider_ids = {
        "transfermarkt": (
            "spieler",
            player["transfermarkt_id"],
        ),
        "wyscout": (
            "player",
            player["wyscout_id"],
        ),
        "opta": (
            "person",
            player["opta_id"],
        ),
        "api_football": (
            "player",
            player["api_football_id"],
        ),
        "sportmonks": (
            "player",
            player["sportmonks_id"],
        ),
    }

    for provider, (
        namespace,
        external_id,
    ) in provider_ids.items():

        if external_id is None:
            continue

        external_id = str(external_id).strip()

        url = build_url(
            provider,
            namespace,
            external_id,
        )

        print()
        print(
            f"{provider:18} "
            f"{namespace:18} "
            f"ID={external_id}"
        )

        if url:
            print(f"  Testing URL: {url}")

            test_result = test_public_url(url)

            print(
                f"  Result: "
                f"{test_result['reason']}"
            )

            if test_result["position_found"]:
                print(
                    "  Possible position text found: "
                    + ", ".join(
                        test_result["position_values"]
                    )
                )
            else:
                print(
                    "  Position not confirmed."
                )

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

        else:
            test_result = {
                "attempted": False,
                "http_status": None,
                "accessible": False,
                "reason": (
                    "AUTHENTICATED_ENDPOINT_NOT_TESTED"
                ),
                "content_type": None,
                "position_found": False,
                "position_values": [],
            }

            print(
                "  Not queried: authenticated/"
                "commercial access required."
            )

        results.append({
            "reep_id": player["reep_id"],
            "label": player["label"],
            "gender": player["gender"],
            "provider": provider,
            "namespace": namespace,
            "external_id": external_id,
            "url": url,
            **test_result,
        })

# ------------------------------------------------------------
# Summary
# ------------------------------------------------------------

print()
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print()

providers = [
    "transfermarkt",
    "wyscout",
    "opta",
    "api_football",
    "sportmonks",
]

for provider in providers:

    provider_results = [
        r for r in results
        if r["provider"] == provider
    ]

    attempted = sum(
        1
        for r in provider_results
        if r["attempted"]
    )

    accessible = sum(
        1
        for r in provider_results
        if r["accessible"]
    )

    position_found = sum(
        1
        for r in provider_results
        if r["position_found"]
    )

    print(
        f"{provider:18} "
        f"IDs={len(provider_results):>2} "
        f"attempted={attempted:>2} "
        f"HTTP-OK={accessible:>2} "
        f"possible-position={position_found:>2}"
    )

print()

# ------------------------------------------------------------
# Interpretation
# ------------------------------------------------------------

print("=" * 70)
print("INTERPRETATION")
print("=" * 70)
print()
print(
    "IMPORTANT:"
)
print(
    "A failed HTTP request does NOT mean the provider lacks "
    "position data."
)
print(
    "It may mean authentication, subscription, anti-bot "
    "protection, or a changed URL."
)
print()
print(
    "A detected keyword is NOT yet accepted as canonical "
    "position evidence."
)
print(
    "This test only establishes whether position information "
    "appears retrievable."
)
print()

# ------------------------------------------------------------
# Save JSON
# ------------------------------------------------------------

report = {
    "audit": (
        "REEP Actual Position Provider Data Test"
    ),
    "read_only": True,
    "source_database": str(SOURCE_DB),
    "total_reep_players": int(total_players),
    "sample_size": len(sample),
    "sample_players": sample,
    "provider_results": results,
    "database_modified": False,
    "v1_master_modified": False,
    "interpretation": (
        "This is an access/capability test only. "
        "HTTP failure does not prove absence of position data. "
        "Detected position text is not canonical evidence."
    ),
}

OUTPUT_JSON.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

# ------------------------------------------------------------
# Save CSV
# ------------------------------------------------------------

csv_fields = [
    "reep_id",
    "label",
    "gender",
    "provider",
    "namespace",
    "external_id",
    "url",
    "attempted",
    "http_status",
    "accessible",
    "reason",
    "content_type",
    "position_found",
    "position_values",
]

with OUTPUT_CSV.open(
    "w",
    newline="",
    encoding="utf-8-sig",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=csv_fields,
    )

    writer.writeheader()

    for row in results:
        output_row = dict(row)

        output_row["position_values"] = (
            ";".join(
                output_row["position_values"]
            )
        )

        writer.writerow(output_row)

con.close()

print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
print()
print("JSON report:")
print(OUTPUT_JSON)
print()
print("CSV report:")
print(OUTPUT_CSV)
print()
print("No source database changes were made.")
print("No v1.0.0 master changes were made.")
print()