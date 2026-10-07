import duckdb
import json
from pathlib import Path
from datetime import datetime


# ============================================================
# REEP PLAYER POSITION ENRICHMENT — CUMULATIVE AUDIT
# ============================================================

DB_PATH = Path("output/reep-player-position-evidence.duckdb")
REPORT_PATH = Path("output/reep-player-position-enrichment-cumulative-audit.json")


print("=" * 80)
print("REEP PLAYER POSITION ENRICHMENT — CUMULATIVE AUDIT")
print("=" * 80)
print()
print("READ-ONLY — production database will NOT be modified.")
print()
print(f"Database: {DB_PATH}")
print(f"Report:   {REPORT_PATH}")
print()


if not DB_PATH.exists():
    print("ERROR: Production database not found.")
    raise SystemExit(1)


conn = duckdb.connect(str(DB_PATH), read_only=True)


# ============================================================
# HELPERS
# ============================================================

def scalar(sql):
    try:
        return conn.execute(sql).fetchone()[0]
    except Exception as exc:
        print(f"QUERY ERROR: {exc}")
        return None


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"{name:<55} {status}")
    if detail:
        print(f"  {detail}")
    return status == "PASS"


audit = {
    "audit_timestamp": datetime.utcnow().isoformat() + "Z",
    "database": str(DB_PATH),
    "status": "PASS",
    "checks": {},
    "counts": {},
}


# ============================================================
# REQUIRED TABLES
# ============================================================

print("=" * 80)
print("CHECKING REQUIRED TABLES")
print("=" * 80)

required_tables = [
    "database_metadata",
    "player_position",
    "player_position_claims",
    "position_fetch_log",
]

existing_tables = {
    row[0]
    for row in conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main'"
    ).fetchall()
}

for table in required_tables:
    passed = table in existing_tables
    audit["checks"][f"table_{table}"] = passed
    check(table, passed)

if not all(audit["checks"][f"table_{t}"] for t in required_tables):
    audit["status"] = "FAIL"
    conn.close()
    REPORT_PATH.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print()
    print("STATUS: FAIL")
    print("Required tables are missing.")
    raise SystemExit(1)

print()


# ============================================================
# DATABASE COUNTS
# ============================================================

print("=" * 80)
print("DATABASE COUNTS")
print("=" * 80)

canonical_players = scalar(
    "SELECT COUNT(*) FROM player_position"
)

position_claims = scalar(
    "SELECT COUNT(*) FROM player_position_claims"
)

fetch_rows = scalar(
    "SELECT COUNT(*) FROM position_fetch_log"
)

print(f"Canonical players:       {canonical_players:,}")
print(f"Position claims:         {position_claims:,}")
print(f"Fetch log rows:          {fetch_rows:,}")

audit["counts"]["canonical_players"] = canonical_players
audit["counts"]["position_claims"] = position_claims
audit["counts"]["fetch_log_rows"] = fetch_rows

print()


# ============================================================
# CANONICAL PLAYER ID INTEGRITY
# ============================================================

print("=" * 80)
print("CANONICAL PLAYER ID INTEGRITY")
print("=" * 80)

duplicate_canonical = scalar("""
    SELECT COUNT(*)
    FROM (
        SELECT reep_id
        FROM player_position
        GROUP BY reep_id
        HAVING COUNT(*) > 1
    )
""")

null_canonical = scalar("""
    SELECT COUNT(*)
    FROM player_position
    WHERE reep_id IS NULL
       OR TRIM(reep_id) = ''
""")

audit["counts"]["duplicate_canonical_ids"] = duplicate_canonical
audit["counts"]["null_canonical_ids"] = null_canonical

audit["checks"]["duplicate_canonical_ids"] = check(
    "Duplicate canonical player IDs",
    duplicate_canonical == 0,
    f"count={duplicate_canonical}"
)

audit["checks"]["null_canonical_ids"] = check(
    "Null/empty canonical player IDs",
    null_canonical == 0,
    f"count={null_canonical}"
)

print()


# ============================================================
# FETCH LOG INTEGRITY
# ============================================================

print("=" * 80)
print("FETCH LOG INTEGRITY")
print("=" * 80)

duplicate_fetch = scalar("""
    SELECT COUNT(*)
    FROM (
        SELECT reep_id
        FROM position_fetch_log
        GROUP BY reep_id
        HAVING COUNT(*) > 1
    )
""")

null_fetch = scalar("""
    SELECT COUNT(*)
    FROM position_fetch_log
    WHERE reep_id IS NULL
       OR TRIM(reep_id) = ''
""")

orphan_fetch = scalar("""
    SELECT COUNT(*)
    FROM position_fetch_log f
    LEFT JOIN player_position p
      ON f.reep_id = p.reep_id
    WHERE p.reep_id IS NULL
""")

count_match = canonical_players == fetch_rows

audit["counts"]["duplicate_fetch_ids"] = duplicate_fetch
audit["counts"]["null_fetch_ids"] = null_fetch
audit["counts"]["orphan_fetch_ids"] = orphan_fetch

audit["checks"]["duplicate_fetch_ids"] = check(
    "Duplicate fetch-log player IDs",
    duplicate_fetch == 0,
    f"count={duplicate_fetch}"
)

audit["checks"]["null_fetch_ids"] = check(
    "Null/empty fetch-log player IDs",
    null_fetch == 0,
    f"count={null_fetch}"
)

audit["checks"]["orphan_fetch_ids"] = check(
    "Fetch-log orphan player IDs",
    orphan_fetch == 0,
    f"count={orphan_fetch}"
)

audit["checks"]["canonical_fetch_count_match"] = check(
    "Canonical/fetch-log count match",
    count_match,
    f"canonical={canonical_players}, fetch_log={fetch_rows}"
)

print()


# ============================================================
# POSITION CLAIM INTEGRITY
# ============================================================

print("=" * 80)
print("POSITION CLAIM INTEGRITY")
print("=" * 80)

orphan_claims = scalar("""
    SELECT COUNT(*)
    FROM player_position_claims c
    LEFT JOIN player_position p
      ON c.reep_id = p.reep_id
    WHERE p.reep_id IS NULL
""")

null_claim_ids = scalar("""
    SELECT COUNT(*)
    FROM player_position_claims
    WHERE reep_id IS NULL
       OR TRIM(reep_id) = ''
""")

empty_source_positions = scalar("""
    SELECT COUNT(*)
    FROM player_position_claims
    WHERE position IS NULL
       OR TRIM(position) = ''
""")

empty_normalized_positions = scalar("""
    SELECT COUNT(*)
    FROM player_position_claims
    WHERE position_normalized IS NULL
       OR TRIM(position_normalized) = ''
""")

audit["counts"]["orphan_position_claims"] = orphan_claims
audit["counts"]["null_claim_player_ids"] = null_claim_ids
audit["counts"]["empty_source_positions"] = empty_source_positions
audit["counts"]["empty_normalized_positions"] = empty_normalized_positions

audit["checks"]["orphan_position_claims"] = check(
    "Orphan position claims",
    orphan_claims == 0,
    f"count={orphan_claims}"
)

audit["checks"]["null_claim_player_ids"] = check(
    "Null/empty claim player IDs",
    null_claim_ids == 0,
    f"count={null_claim_ids}"
)

audit["checks"]["empty_source_positions"] = check(
    "Empty source positions",
    empty_source_positions == 0,
    f"count={empty_source_positions}"
)

audit["checks"]["empty_normalized_positions"] = check(
    "Empty normalized positions",
    empty_normalized_positions == 0,
    f"count={empty_normalized_positions}"
)

print()


# ============================================================
# POSITION TYPE VALIDATION
# ============================================================

print("=" * 80)
print("POSITION TYPE VALIDATION")
print("=" * 80)

position_type_rows = conn.execute("""
    SELECT
        position_type,
        COUNT(*) AS count
    FROM player_position_claims
    GROUP BY position_type
    ORDER BY position_type
""").fetchall()

print("Position type distribution:")

position_types = {}

for position_type, count in position_type_rows:
    position_types[position_type] = count
    print(f"  {position_type}: {count:,}")

invalid_position_types = scalar("""
    SELECT COUNT(*)
    FROM player_position_claims
    WHERE position_type NOT IN ('main', 'other')
       OR position_type IS NULL
       OR TRIM(position_type) = ''
""")

audit["counts"]["invalid_position_types"] = invalid_position_types
audit["position_type_distribution"] = position_types

audit["checks"]["valid_position_types"] = check(
    "Valid position types",
    invalid_position_types == 0,
    f"invalid_count={invalid_position_types}"
)

print()


# ============================================================
# NORMALIZED POSITION VALIDATION
# ============================================================

print("=" * 80)
print("NORMALIZED POSITION VALIDATION")
print("=" * 80)

normalized_rows = conn.execute("""
    SELECT
        position_normalized,
        COUNT(*) AS count
    FROM player_position_claims
    GROUP BY position_normalized
    ORDER BY position_normalized
""").fetchall()

print("Normalized position distribution:")

normalized_positions = {}

for position, count in normalized_rows:
    normalized_positions[position] = count
    print(f"  {position}: {count:,}")

audit["normalized_position_distribution"] = normalized_positions

print()

# ============================================================
# CANONICAL POSITION STATUS VALIDATION
# ============================================================

print("=" * 80)
print("CANONICAL POSITION STATUS VALIDATION")
print("=" * 80)

status_rows = conn.execute("""
    SELECT
        position_status,
        COUNT(*) AS count
    FROM player_position
    GROUP BY position_status
    ORDER BY position_status
""").fetchall()

print("Position status distribution:")

position_statuses = {}

for status, count in status_rows:
    position_statuses[status] = count
    print(f"  {status}: {count:,}")

audit["position_status_distribution"] = position_statuses

print()


# ============================================================
# CANONICAL EVIDENCE COUNT VALIDATION
# ============================================================

print("=" * 80)
print("CANONICAL EVIDENCE COUNT VALIDATION")
print("=" * 80)

evidence_mismatches = scalar("""
    SELECT COUNT(*)
    FROM player_position p
    LEFT JOIN (
        SELECT
            reep_id,
            COUNT(*) AS claim_count
        FROM player_position_claims
        GROUP BY reep_id
    ) c
      ON p.reep_id = c.reep_id
    WHERE p.evidence_count != COALESCE(c.claim_count, 0)
""")

provider_mismatches = scalar("""
    SELECT COUNT(*)
    FROM player_position p
    LEFT JOIN (
        SELECT
            reep_id,
            COUNT(DISTINCT provider) AS provider_count
        FROM player_position_claims
        GROUP BY reep_id
    ) c
      ON p.reep_id = c.reep_id
    WHERE p.provider_count != COALESCE(c.provider_count, 0)
""")

audit["counts"]["evidence_count_mismatches"] = evidence_mismatches
audit["counts"]["provider_count_mismatches"] = provider_mismatches

audit["checks"]["evidence_count_matches"] = check(
    "Canonical evidence_count matches claims",
    evidence_mismatches == 0,
    f"mismatches={evidence_mismatches}"
)

audit["checks"]["provider_count_matches"] = check(
    "Canonical provider_count matches providers",
    provider_mismatches == 0,
    f"mismatches={provider_mismatches}"
)

print()


# ============================================================
# FETCH STATUS VALIDATION
# ============================================================

print("=" * 80)
print("FETCH STATUS VALIDATION")
print("=" * 80)

fetch_status_rows = conn.execute("""
    SELECT
        fetch_status,
        COUNT(*) AS count
    FROM position_fetch_log
    GROUP BY fetch_status
    ORDER BY fetch_status
""").fetchall()

fetch_status_distribution = {}

for status, count in fetch_status_rows:
    fetch_status_distribution[status] = count
    print(f"  {status}: {count:,}")

audit["fetch_status_distribution"] = fetch_status_distribution

print()


# ============================================================
# HTTP STATUS VALIDATION
# ============================================================

print("=" * 80)
print("HTTP STATUS VALIDATION")
print("=" * 80)

http_rows = conn.execute("""
    SELECT
        http_status,
        COUNT(*) AS count
    FROM position_fetch_log
    GROUP BY http_status
    ORDER BY http_status
""").fetchall()

http_distribution = {}

for status, count in http_rows:
    http_distribution[str(status)] = count
    print(f"  HTTP {status}: {count:,}")

audit["http_status_distribution"] = http_distribution

print()


# ============================================================
# PROVIDER VALIDATION
# ============================================================

print("=" * 80)
print("PROVIDER VALIDATION")
print("=" * 80)

provider_rows = conn.execute("""
    SELECT
        provider,
        COUNT(*) AS count
    FROM player_position_claims
    GROUP BY provider
    ORDER BY provider
""").fetchall()

provider_distribution = {}

for provider, count in provider_rows:
    provider_distribution[provider] = count
    print(f"  {provider}: {count:,}")

audit["provider_distribution"] = provider_distribution

print()


# ============================================================
# FINAL STATUS
# ============================================================

failed_checks = [
    name
    for name, passed in audit["checks"].items()
    if not passed
]

if failed_checks:
    audit["status"] = "FAIL"
else:
    audit["status"] = "PASS"


conn.close()


# ============================================================
# SAVE REPORT
# ============================================================

REPORT_PATH.write_text(
    json.dumps(audit, indent=2),
    encoding="utf-8"
)


print("=" * 80)
print("FINAL AUDIT STATUS")
print("=" * 80)

if audit["status"] == "PASS":
    print("STATUS: PASS")
    print()
    print("The cumulative position database passed all integrity checks.")
else:
    print("STATUS: FAIL")
    print()
    print("Failed checks:")
    for item in failed_checks:
        print(f"  - {item}")

print()
print(f"Audit report saved to:")
print(f"  {REPORT_PATH}")
print("=" * 80)