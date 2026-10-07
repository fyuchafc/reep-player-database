import duckdb
import json
from pathlib import Path
from collections import Counter


# ============================================================
# REEP v1.1 — AUDIT PLAYER DOB EVIDENCE LAYER
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DOB_DB = ROOT / "output" / "reep-player-dob-evidence.duckdb"
REPORT_JSON = ROOT / "output" / "reep-player-dob-evidence-audit.json"
REPORT_CSV = ROOT / "output" / "reep-player-dob-evidence-audit.csv"


print("=" * 70)
print("REEP v1.1 — AUDIT PLAYER DOB EVIDENCE LAYER")
print("=" * 70)
print()
print("READ-ONLY — derived DOB database will NOT be modified.")
print()
print(f"DOB database:")
print(DOB_DB)
print()


# ============================================================
# OPEN
# ============================================================

if not DOB_DB.exists():
    print("ERROR: DOB evidence database does not exist.")
    raise SystemExit(1)

print("Opening DOB evidence database READ-ONLY...")
con = duckdb.connect(str(DOB_DB), read_only=True)
print("Connected successfully.")
print()


# ============================================================
# REQUIRED TABLES
# ============================================================

print("=" * 70)
print("CHECKING REQUIRED TABLES")
print("=" * 70)

tables = {
    row[0]
    for row in con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        """
    ).fetchall()
}

required_tables = {
    "player_dob_claims",
    "player_dob",
    "database_metadata",
}

table_results = {}

for table in sorted(required_tables):
    found = table in tables
    table_results[table] = found
    print(f"{table:<25} {'FOUND' if found else 'MISSING'}")

print()

if not all(table_results.values()):
    print("FINAL STATUS: FAIL")
    con.close()
    raise SystemExit(1)


# ============================================================
# COUNTS
# ============================================================

player_row_count = con.execute(
    "SELECT COUNT(*) FROM player_dob"
).fetchone()[0]

claim_row_count = con.execute(
    "SELECT COUNT(*) FROM player_dob_claims"
).fetchone()[0]

metadata_row_count = con.execute(
    "SELECT COUNT(*) FROM database_metadata"
).fetchone()[0]

print("=" * 70)
print("TABLE COUNTS")
print("=" * 70)

print(f"player_dob rows:          {player_row_count:,}")
print(f"player_dob_claims rows:   {claim_row_count:,}")
print(f"database_metadata rows:   {metadata_row_count:,}")
print()


# ============================================================
# PLAYER ID QUALITY
# ============================================================

duplicate_players = con.execute(
    """
    SELECT COUNT(*)
    FROM (
        SELECT reep_id
        FROM player_dob
        GROUP BY reep_id
        HAVING COUNT(*) > 1
    )
    """
).fetchone()[0]

null_player_ids = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE reep_id IS NULL
       OR TRIM(reep_id) = ''
    """
).fetchone()[0]

null_claim_player_ids = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob_claims
    WHERE reep_id IS NULL
       OR TRIM(reep_id) = ''
    """
).fetchone()[0]

print("=" * 70)
print("PLAYER ID QUALITY")
print("=" * 70)

print(f"Duplicate player IDs:       {duplicate_players:,}")
print(f"NULL/empty player IDs:      {null_player_ids:,}")
print(f"NULL/empty claim IDs:       {null_claim_player_ids:,}")
print()


# ============================================================
# REFERENTIAL INTEGRITY
# ============================================================

orphan_claims = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob_claims c
    LEFT JOIN player_dob p
        ON p.reep_id = c.reep_id
    WHERE p.reep_id IS NULL
    """
).fetchone()[0]

print("=" * 70)
print("REFERENTIAL INTEGRITY")
print("=" * 70)
print(f"Orphan claim rows:          {orphan_claims:,}")
print()


# ============================================================
# STATUS DISTRIBUTION
# ============================================================

status_rows = con.execute(
    """
    SELECT dob_status, COUNT(*)
    FROM player_dob
    GROUP BY dob_status
    ORDER BY COUNT(*) DESC, dob_status
    """
).fetchall()

status_distribution = {
    str(status): count
    for status, count in status_rows
}

print("=" * 70)
print("DOB STATUS DISTRIBUTION")
print("=" * 70)

for status, count in status_rows:
    print(f"{str(status):<35} {count:>10,}")

print()


# ============================================================
# CANONICAL PRECISION
# ============================================================

precision_rows = con.execute(
    """
    SELECT
        COALESCE(dob_precision, '[NULL]') AS precision,
        COUNT(*)
    FROM player_dob
    GROUP BY precision
    ORDER BY COUNT(*) DESC, precision
    """
).fetchall()

precision_distribution = {
    str(precision): count
    for precision, count in precision_rows
}

print("=" * 70)
print("CANONICAL DOB PRECISION")
print("=" * 70)

for precision, count in precision_rows:
    print(f"{precision:<35} {count:>10,}")

print()


# ============================================================
# RAW CLAIM RANK
# ============================================================

rank_rows = con.execute(
    """
    SELECT
        COALESCE(rank, '[NULL]') AS rank,
        COUNT(*)
    FROM player_dob_claims
    GROUP BY rank
    ORDER BY COUNT(*) DESC, rank
    """
).fetchall()

rank_distribution = {
    str(rank): count
    for rank, count in rank_rows
}

print("=" * 70)
print("RAW CLAIM RANK DISTRIBUTION")
print("=" * 70)

for rank, count in rank_rows:
    print(f"{rank:<35} {count:>10,}")

print()


# ============================================================
# RAW CLAIM PRECISION
# ============================================================

claim_precision_rows = con.execute(
    """
    SELECT
        COALESCE(precision, '[NULL]') AS precision,
        COUNT(*)
    FROM player_dob_claims
    GROUP BY precision
    ORDER BY COUNT(*) DESC, precision
    """
).fetchall()

claim_precision_distribution = {
    str(precision): count
    for precision, count in claim_precision_rows
}

print("=" * 70)
print("RAW CLAIM PRECISION DISTRIBUTION")
print("=" * 70)

for precision, count in claim_precision_rows:
    print(f"{precision:<35} {count:>10,}")

print()


# ============================================================
# CLAIM COUNT CONSISTENCY
# ============================================================

claim_count_mismatches = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob p
    LEFT JOIN (
        SELECT reep_id, COUNT(*) AS actual_claim_count
        FROM player_dob_claims
        GROUP BY reep_id
    ) c
        ON c.reep_id = p.reep_id
    WHERE COALESCE(c.actual_claim_count, 0) <> p.claim_count
    """
).fetchone()[0]

preferred_count_mismatches = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob p
    LEFT JOIN (
        SELECT
            reep_id,
            COUNT(*) FILTER (
                WHERE LOWER(TRIM(rank)) = 'preferred'
            ) AS actual_count
        FROM player_dob_claims
        GROUP BY reep_id
    ) c
        ON c.reep_id = p.reep_id
    WHERE COALESCE(c.actual_count, 0) <> p.preferred_claim_count
    """
).fetchone()[0]

normal_count_mismatches = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob p
    LEFT JOIN (
        SELECT
            reep_id,
            COUNT(*) FILTER (
                WHERE LOWER(TRIM(rank)) = 'normal'
            ) AS actual_count
        FROM player_dob_claims
        GROUP BY reep_id
    ) c
        ON c.reep_id = p.reep_id
    WHERE COALESCE(c.actual_count, 0) <> p.normal_claim_count
    """
).fetchone()[0]

deprecated_count_mismatches = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob p
    LEFT JOIN (
        SELECT
            reep_id,
            COUNT(*) FILTER (
                WHERE LOWER(TRIM(rank)) = 'deprecated'
            ) AS actual_count
        FROM player_dob_claims
        GROUP BY reep_id
    ) c
        ON c.reep_id = p.reep_id
    WHERE COALESCE(c.actual_count, 0) <> p.deprecated_claim_count
    """
).fetchone()[0]

print("=" * 70)
print("CLAIM COUNT CONSISTENCY")
print("=" * 70)

print(f"Total claim count mismatches:       {claim_count_mismatches:,}")
print(f"Preferred count mismatches:         {preferred_count_mismatches:,}")
print(f"Normal count mismatches:            {normal_count_mismatches:,}")
print(f"Deprecated count mismatches:        {deprecated_count_mismatches:,}")
print()


# ============================================================
# STATUS LOGIC
# ============================================================

logic_errors = {}

logic_errors["supported_preferred_without_preferred"] = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob_status = 'supported_preferred'
      AND preferred_claim_count = 0
    """
).fetchone()[0]

logic_errors["supported_without_dob"] = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob_status = 'supported'
      AND (dob IS NULL OR TRIM(dob) = '')
    """
).fetchone()[0]

logic_errors["supported_with_preferred"] = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob_status = 'supported'
      AND preferred_claim_count > 0
    """
).fetchone()[0]

logic_errors["conflicted_with_canonical_dob"] = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob_status = 'conflicted'
      AND dob IS NOT NULL
      AND TRIM(dob) <> ''
    """
).fetchone()[0]

logic_errors["no_dob_with_canonical_dob"] = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob_status = 'no_dob'
      AND dob IS NOT NULL
      AND TRIM(dob) <> ''
    """
).fetchone()[0]

logic_errors["no_dob_with_claims"] = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob_status = 'no_dob'
      AND claim_count <> 0
    """
).fetchone()[0]

logic_errors["canonical_dob_without_precision"] = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob IS NOT NULL
      AND TRIM(dob) <> ''
      AND (
          dob_precision IS NULL
          OR TRIM(dob_precision) = ''
      )
    """
).fetchone()[0]

print("=" * 70)
print("CANONICAL STATUS LOGIC AUDIT")
print("=" * 70)

for name, count in logic_errors.items():
    print(f"{name:<45} {count:>8,}")

print()


# ============================================================
# CONFLICT AUDIT
# ============================================================

conflicted_rows = con.execute(
    """
    SELECT
        reep_id,
        label,
        source_qid,
        resolved_qid,
        claim_count,
        preferred_claim_count,
        normal_claim_count,
        deprecated_claim_count,
        dob,
        dob_precision,
        dob_status,
        evidence_reason
    FROM player_dob
    WHERE dob_status = 'conflicted'
    ORDER BY source_qid, reep_id
    """
).fetchall()

conflict_players = len(conflicted_rows)

print("=" * 70)
print("CONFLICT AUDIT")
print("=" * 70)

print(f"Conflicted players:          {conflict_players:,}")

conflict_reason_counts = Counter(
    row[11] if row[11] else "[NULL]"
    for row in conflicted_rows
)

for reason, count in conflict_reason_counts.most_common():
    print(f"{reason:<45} {count:>8,}")

print()


# ============================================================
# DUPLICATE QID PRESERVATION
# ============================================================

duplicate_qid_rows = con.execute(
    """
    SELECT
        source_qid,
        COUNT(DISTINCT reep_id) AS mapped_player_count
    FROM player_dob
    WHERE source_qid IS NOT NULL
      AND TRIM(source_qid) <> ''
    GROUP BY source_qid
    HAVING COUNT(DISTINCT reep_id) > 1
    ORDER BY source_qid
    """
).fetchall()

print("=" * 70)
print("DUPLICATE QID PRESERVATION")
print("=" * 70)

print(
    f"QIDs mapped to multiple REEP players: "
    f"{len(duplicate_qid_rows):,}"
)

duplicate_qid_details = []

for qid_value, mapped_player_count in duplicate_qid_rows:

    players_for_qid = con.execute(
        """
        SELECT
            reep_id,
            label,
            dob,
            dob_status
        FROM player_dob
        WHERE source_qid = ?
        ORDER BY reep_id
        """,
        [qid_value],
    ).fetchall()

    player_ids = {
        row[0]
        for row in players_for_qid
    }

    duplicate_qid_details.append(
        {
            "qid": qid_value,
            "player_count": mapped_player_count,
            "player_ids": sorted(player_ids),
            "players": [
                {
                    "reep_id": row[0],
                    "label": row[1],
                    "dob": row[2],
                    "dob_status": row[3],
                }
                for row in players_for_qid
            ],
        }
    )

    print()
    print(f"QID: {qid_value}")

    for row in players_for_qid:
        print(
            f"  {row[0]} | {row[1]} | "
            f"DOB={row[2]} | STATUS={row[3]}"
        )


# ============================================================
# EXPECTED DUPLICATE QIDS
# ============================================================

expected_duplicate_qids = {
    "Q30103478": {
        "rp9ecbbb4d0876c7",
        "rpb9bade1645adf9",
    },
    "Q56611021": {
        "rp802f7e130c21a0",
        "rp9433019ee9f020",
    },
}

actual_duplicate_map = {
    detail["qid"]: set(detail["player_ids"])
    for detail in duplicate_qid_details
}

duplicate_qid_errors = []

for expected_qid, expected_players in expected_duplicate_qids.items():

    actual_players = actual_duplicate_map.get(
        expected_qid,
        set()
    )

    if actual_players != expected_players:
        duplicate_qid_errors.append(
            {
                "qid": expected_qid,
                "expected": sorted(expected_players),
                "actual": sorted(actual_players),
            }
        )

        print()
        print("DUPLICATE QID MISMATCH")
        print(f"QID:      {expected_qid}")
        print(f"Expected: {sorted(expected_players)}")
        print(f"Actual:   {sorted(actual_players)}")


print()


# ============================================================
# QID QUALITY
# ============================================================

redirected_player_rows = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE redirected = TRUE
    """
).fetchone()[0]

source_qid_missing = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE source_qid IS NULL
       OR TRIM(source_qid) = ''
    """
).fetchone()[0]

resolved_qid_missing = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE resolved_qid IS NULL
       OR TRIM(resolved_qid) = ''
    """
).fetchone()[0]

print("=" * 70)
print("QID QUALITY")
print("=" * 70)

print(f"Redirected player rows:      {redirected_player_rows:,}")
print(f"Missing source QIDs:         {source_qid_missing:,}")
print(f"Missing resolved QIDs:       {resolved_qid_missing:,}")
print()


# ============================================================
# CANONICAL DOB VALIDITY
# ============================================================

canonical_dob_with_conflict = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob_status = 'conflicted'
      AND dob IS NOT NULL
      AND TRIM(dob) <> ''
    """
).fetchone()[0]

canonical_dob_bad_format = con.execute(
    """
    SELECT COUNT(*)
    FROM player_dob
    WHERE dob IS NOT NULL
      AND TRIM(dob) <> ''
      AND TRY_CAST(dob AS DATE) IS NULL
    """
).fetchone()[0]

print("=" * 70)
print("CANONICAL DOB VALIDITY")
print("=" * 70)

print(
    f"Conflicted players with canonical DOB: "
    f"{canonical_dob_with_conflict:,}"
)

print(
    f"Invalid canonical DOB date format:     "
    f"{canonical_dob_bad_format:,}"
)

print()


# ============================================================
# EVIDENCE REASONS
# ============================================================

reason_rows = con.execute(
    """
    SELECT
        COALESCE(evidence_reason, '[NULL]') AS reason,
        COUNT(*)
    FROM player_dob
    GROUP BY reason
    ORDER BY COUNT(*) DESC, reason
    """
).fetchall()

reason_distribution = {
    str(reason): count
    for reason, count in reason_rows
}

print("=" * 70)
print("EVIDENCE REASON DISTRIBUTION")
print("=" * 70)

for reason, count in reason_rows:
    print(f"{reason:<45} {count:>10,}")

print()


# ============================================================
# CLAIM SOURCES
# ============================================================

source_rows = con.execute(
    """
    SELECT
        COALESCE(source, '[NULL]') AS source,
        COUNT(*)
    FROM player_dob_claims
    GROUP BY source
    ORDER BY COUNT(*) DESC, source
    """
).fetchall()

source_distribution = {
    str(source): count
    for source, count in source_rows
}

print("=" * 70)
print("CLAIM SOURCE DISTRIBUTION")
print("=" * 70)

for source, count in source_rows:
    print(f"{source:<45} {count:>10,}")

print()


# ============================================================
# EXPECTED VALUES
# ============================================================

expected = {
    "player_count": 133047,
    "status_distribution": {
        "conflicted": 1665,
        "no_dob": 32950,
        "supported": 97764,
        "supported_preferred": 668,
    },
    "canonical_day": 98432,
    "duplicate_players": 0,
    "orphan_claims": 0,
    "null_player_ids": 0,
    "null_claim_player_ids": 0,
    "claim_count_mismatches": 0,
    "preferred_count_mismatches": 0,
    "normal_count_mismatches": 0,
    "deprecated_count_mismatches": 0,
    "source_qid_missing": 0,
    "resolved_qid_missing": 0,
    "canonical_dob_with_conflict": 0,
    "canonical_dob_bad_format": 0,
}


# ============================================================
# FINAL STATUS
# ============================================================

failures = []

if player_row_count != expected["player_count"]:
    failures.append(
        f"player_count expected {expected['player_count']} "
        f"but found {player_row_count}"
    )

for status, expected_count in expected["status_distribution"].items():

    actual = status_distribution.get(status, 0)

    if actual != expected_count:
        failures.append(
            f"status {status}: expected "
            f"{expected_count}, found {actual}"
        )

canonical_day = precision_distribution.get("day", 0)

if canonical_day != expected["canonical_day"]:
    failures.append(
        f"canonical day precision expected "
        f"{expected['canonical_day']} "
        f"but found {canonical_day}"
    )

checks = {
    "duplicate_players": duplicate_players,
    "orphan_claims": orphan_claims,
    "null_player_ids": null_player_ids,
    "null_claim_player_ids": null_claim_player_ids,
    "claim_count_mismatches": claim_count_mismatches,
    "preferred_count_mismatches": preferred_count_mismatches,
    "normal_count_mismatches": normal_count_mismatches,
    "deprecated_count_mismatches": deprecated_count_mismatches,
    "source_qid_missing": source_qid_missing,
    "resolved_qid_missing": resolved_qid_missing,
    "canonical_dob_with_conflict": canonical_dob_with_conflict,
    "canonical_dob_bad_format": canonical_dob_bad_format,
}

for name, actual in checks.items():

    if actual != expected[name]:
        failures.append(
            f"{name}: expected "
            f"{expected[name]}, found {actual}"
        )

for name, count in logic_errors.items():

    if count != 0:
        failures.append(
            f"{name}: found {count}"
        )

if duplicate_qid_errors:

    for error in duplicate_qid_errors:

        failures.append(
            f"duplicate QID {error['qid']} mismatch: "
            f"expected {error['expected']}, "
            f"actual {error['actual']}"
        )


# ============================================================
# REPORT
# ============================================================

report = {
    "audit": "REEP v1.1 Player DOB Evidence Layer Audit",
    "database": str(DOB_DB),
    "read_only": True,

    "table_results": table_results,

    "counts": {
        "player_dob": player_row_count,
        "player_dob_claims": claim_row_count,
        "database_metadata": metadata_row_count,
    },

    "status_distribution": status_distribution,
    "precision_distribution": precision_distribution,
    "claim_precision_distribution": claim_precision_distribution,
    "rank_distribution": rank_distribution,
    "evidence_reason_distribution": reason_distribution,
    "source_distribution": source_distribution,

    "quality": {
        "duplicate_players": duplicate_players,
        "orphan_claims": orphan_claims,
        "null_player_ids": null_player_ids,
        "null_claim_player_ids": null_claim_player_ids,
    },

    "claim_count_consistency": {
        "claim_count_mismatches": claim_count_mismatches,
        "preferred_count_mismatches": preferred_count_mismatches,
        "normal_count_mismatches": normal_count_mismatches,
        "deprecated_count_mismatches": deprecated_count_mismatches,
    },

    "status_logic": logic_errors,

    "qid_quality": {
        "redirected_player_rows": redirected_player_rows,
        "source_qid_missing": source_qid_missing,
        "resolved_qid_missing": resolved_qid_missing,
    },

    "canonical_dob_validity": {
        "conflicted_with_canonical_dob": canonical_dob_with_conflict,
        "invalid_date_format": canonical_dob_bad_format,
    },

    "duplicate_qids": duplicate_qid_details,
    "duplicate_qid_errors": duplicate_qid_errors,

    "expected_values": expected,

    "failures": failures,

    "final_status": "PASS" if not failures else "FAIL",
}


REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)

with open(REPORT_JSON, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)


# ============================================================
# CSV SUMMARY
# ============================================================

csv_rows = [
    ("player_dob_rows", player_row_count),
    ("player_dob_claim_rows", claim_row_count),
    ("duplicate_player_ids", duplicate_players),
    ("orphan_claim_rows", orphan_claims),
    ("null_player_ids", null_player_ids),
    ("null_claim_player_ids", null_claim_player_ids),
    ("claim_count_mismatches", claim_count_mismatches),
    ("preferred_count_mismatches", preferred_count_mismatches),
    ("normal_count_mismatches", normal_count_mismatches),
    ("deprecated_count_mismatches", deprecated_count_mismatches),
    ("canonical_day_precision", canonical_day),
    ("conflicted_players", status_distribution.get("conflicted", 0)),
    ("no_dob_players", status_distribution.get("no_dob", 0)),
    ("supported_players", status_distribution.get("supported", 0)),
    (
        "supported_preferred_players",
        status_distribution.get("supported_preferred", 0),
    ),
    ("redirected_player_rows", redirected_player_rows),
    ("source_qid_missing", source_qid_missing),
    ("resolved_qid_missing", resolved_qid_missing),
    ("canonical_dob_with_conflict", canonical_dob_with_conflict),
    ("canonical_dob_bad_format", canonical_dob_bad_format),
    ("duplicate_qid_errors", len(duplicate_qid_errors)),
]

with open(REPORT_CSV, "w", encoding="utf-8", newline="") as f:

    f.write("check,value\n")

    for key, value in csv_rows:
        f.write(f"{key},{value}\n")


# ============================================================
# FINAL OUTPUT
# ============================================================

print("=" * 70)
print("FINAL AUDIT STATUS")
print("=" * 70)

if failures:

    print("FINAL STATUS: FAIL")
    print()
    print("FAILURES:")

    for failure in failures:
        print(f"  - {failure}")

else:

    print("FINAL STATUS: PASS")
    print()
    print("All DOB evidence-layer integrity checks passed.")

print()
print(f"JSON REPORT: {REPORT_JSON}")
print(f"CSV REPORT:  {REPORT_CSV}")
print()
print("The DOB evidence database was NOT modified.")
print("The frozen v1.0.0 master was NOT modified.")
print("=" * 70)

con.close()