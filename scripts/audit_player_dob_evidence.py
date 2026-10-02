import csv
import json
import os
import sys
from collections import Counter, defaultdict

import duckdb


# ============================================================
# REEP PLAYER DOB EVIDENCE AUDIT
# ============================================================

print("=" * 70)
print("REEP PLAYER DOB EVIDENCE AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()


# ============================================================
# PATHS
# ============================================================

DB_PATH = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")

CSV_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-dob-evidence.csv"
)

JSON_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-dob-evidence.json"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# DATABASE CHECK
# ============================================================

if not os.path.isfile(DB_PATH):
    raise FileNotFoundError(
        f"Database not found:\n{DB_PATH}"
    )

print("Source database:")
print(DB_PATH)
print()
print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=DB_PATH,
    read_only=True
)

print("Connected successfully.")
print()


# ============================================================
# HELPERS
# ============================================================

def table_exists(table_name):
    row = con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
        """,
        [table_name]
    ).fetchone()

    return row[0] > 0


def get_columns(table_name):
    rows = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ?
        ORDER BY ordinal_position
        """,
        [table_name]
    ).fetchall()

    return [row[0] for row in rows]


def first_existing(columns, candidates):
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


# ============================================================
# REQUIRED TABLES
# ============================================================

print("=" * 70)
print("CHECKING REQUIRED TABLES")
print("=" * 70)

required_tables = [
    "players",
    "overlay_links",
    "overlay_xids",
]

for table in required_tables:
    if table_exists(table):
        print(f"  {table:<20} FOUND")
    else:
        print(f"  {table:<20} MISSING")

print()


# ============================================================
# PLAYER MASTER
# ============================================================

print("=" * 70)
print("LOADING PLAYER MASTER")
print("=" * 70)

player_columns = get_columns("players")

print("Players table columns:")
print(", ".join(player_columns))
print()

player_id_col = first_existing(
    player_columns,
    ["reep_id", "player_id", "id"]
)

label_col = first_existing(
    player_columns,
    ["label", "name", "player_name"]
)

status_col = first_existing(
    player_columns,
    ["status"]
)

gender_col = first_existing(
    player_columns,
    ["gender", "sex"]
)

if not player_id_col:
    raise RuntimeError(
        "Could not detect player ID column in players table."
    )

players = con.execute(
    f"""
    SELECT
        {player_id_col},
        {label_col if label_col else "NULL"},
        {status_col if status_col else "NULL"},
        {gender_col if gender_col else "NULL"}
    FROM players
    """
).fetchall()

player_ids = set()

player_master = {}

for row in players:
    reep_id = row[0]

    if reep_id is None:
        continue

    reep_id = str(reep_id)

    player_ids.add(reep_id)

    player_master[reep_id] = {
        "label": row[1],
        "status": row[2],
        "gender": row[3],
    }

total_players = len(player_ids)

print(f"Total REEP players: {total_players:,}")
print()


# ============================================================
# OVERLAY LINKS
# ============================================================

print("=" * 70)
print("QID / DOB EVIDENCE FROM OVERLAY_LINKS")
print("=" * 70)

overlay_link_columns = get_columns("overlay_links")

print("overlay_links columns:")
print(", ".join(overlay_link_columns))
print()

ol_player_col = first_existing(
    overlay_link_columns,
    ["reep_id", "player_id", "id"]
)

ol_qid_col = first_existing(
    overlay_link_columns,
    ["qid", "wikidata_id"]
)

ol_conf_col = first_existing(
    overlay_link_columns,
    ["confidence", "link_confidence"]
)

ol_dob_col = first_existing(
    overlay_link_columns,
    ["dob_check", "dob_status", "dob_verification"]
)

ol_entity_col = first_existing(
    overlay_link_columns,
    ["entity_type"]
)

if not ol_player_col:
    raise RuntimeError(
        "Could not detect player ID column in overlay_links."
    )

select_parts = [
    ol_player_col
]

select_parts.append(
    ol_qid_col if ol_qid_col else "NULL"
)

select_parts.append(
    ol_conf_col if ol_conf_col else "NULL"
)

select_parts.append(
    ol_dob_col if ol_dob_col else "NULL"
)

select_parts.append(
    ol_entity_col if ol_entity_col else "NULL"
)

overlay_rows = con.execute(
    f"""
    SELECT
        {", ".join(select_parts)}
    FROM overlay_links
    """
).fetchall()

overlay_player_rows = [
    row for row in overlay_rows
    if row[0] is not None and str(row[0]) in player_ids
]

print(
    f"Overlay-link rows belonging to players: "
    f"{len(overlay_player_rows):,}"
)

qid_players = set()
dob_counter = Counter()
confidence_counter = Counter()

player_dob_records = defaultdict(list)

for row in overlay_player_rows:
    reep_id = str(row[0])
    qid = row[1]
    confidence = row[2]
    dob_check = row[3]

    if qid is not None and str(qid).strip():
        qid_players.add(reep_id)

    if dob_check is not None:
        dob_value = str(dob_check).strip()
        if dob_value:
            dob_counter[dob_value] += 1
            player_dob_records[reep_id].append(
                ("overlay_links", dob_value)
            )

    if confidence is not None:
        confidence_counter[str(confidence)] += 1

print(
    f"Players with QID evidence: {len(qid_players):,}"
)

print()


# ============================================================
# EXTERNAL-ID DOB EVIDENCE
# ============================================================

print("=" * 70)
print("EXTERNAL-ID DOB EVIDENCE")
print("=" * 70)

xid_columns = get_columns("overlay_xids")

print("overlay_xids columns:")
print(", ".join(xid_columns))
print()

xid_player_col = first_existing(
    xid_columns,
    ["reep_id", "player_id", "id"]
)

xid_provider_col = first_existing(
    xid_columns,
    ["provider", "source"]
)

xid_dob_col = first_existing(
    xid_columns,
    ["dob_check", "dob_status", "dob_verification"]
)

xid_qid_col = first_existing(
    xid_columns,
    ["qid", "wikidata_id"]
)

if not xid_player_col:
    raise RuntimeError(
        "Could not detect player ID column in overlay_xids."
    )

xid_select = [
    xid_player_col,
    xid_provider_col if xid_provider_col else "NULL",
    xid_dob_col if xid_dob_col else "NULL",
    xid_qid_col if xid_qid_col else "NULL",
]

xid_rows = con.execute(
    f"""
    SELECT
        {", ".join(xid_select)}
    FROM overlay_xids
    """
).fetchall()

xid_player_rows = [
    row for row in xid_rows
    if row[0] is not None and str(row[0]) in player_ids
]

print(
    f"External-ID rows belonging to players: "
    f"{len(xid_player_rows):,}"
)

xid_dob_counter = Counter()
xid_dob_players = defaultdict(set)
xid_provider_dob = Counter()

for row in xid_player_rows:
    reep_id = str(row[0])
    provider = row[1]
    dob_check = row[2]

    if dob_check is not None:
        dob_value = str(dob_check).strip()

        if dob_value:
            xid_dob_counter[dob_value] += 1
            xid_dob_players[dob_value].add(reep_id)

            provider_name = (
                str(provider)
                if provider is not None
                else "unknown"
            )

            xid_provider_dob[
                (provider_name, dob_value)
            ] += 1

            player_dob_records[reep_id].append(
                (provider_name, dob_value)
            )

print()


# ============================================================
# DOB STATUS CLASSIFICATION
# ============================================================

print("=" * 70)
print("DOB EVIDENCE CLASSIFICATION")
print("=" * 70)

all_dob_evidence_players = set(player_dob_records.keys())

dob_agrees_players = set()
dob_unverified_players = set()
dob_other_players = set()

for reep_id, records in player_dob_records.items():

    values = {
        value.lower().strip()
        for _, value in records
        if value
    }

    if "dob-agrees" in values:
        dob_agrees_players.add(reep_id)

    if "dob-unverified" in values:
        dob_unverified_players.add(reep_id)

    other_values = values - {
        "dob-agrees",
        "dob-unverified",
    }

    if other_values:
        dob_other_players.add(reep_id)

print(
    f"Players with any DOB evidence: "
    f"{len(all_dob_evidence_players):,}"
)

print(
    f"Players with dob-agrees evidence: "
    f"{len(dob_agrees_players):,}"
)

print(
    f"Players with dob-unverified evidence: "
    f"{len(dob_unverified_players):,}"
)

print(
    f"Players with other DOB statuses: "
    f"{len(dob_other_players):,}"
)

print()


# ============================================================
# PLAYER-LEVEL STATUS
# ============================================================

player_status_counter = Counter()

player_rows = []

for reep_id in sorted(player_ids):

    master = player_master.get(
        reep_id,
        {}
    )

    records = player_dob_records.get(
        reep_id,
        []
    )

    dob_values = sorted({
        value
        for _, value in records
        if value
    })

    sources = sorted({
        source
        for source, _ in records
    })

    statuses = {
        value.lower().strip()
        for _, value in records
        if value
    }

    has_qid = reep_id in qid_players

    has_dob_agrees = (
        "dob-agrees" in statuses
    )

    has_dob_unverified = (
        "dob-unverified" in statuses
    )

    if has_dob_agrees:
        evidence_status = "dob_agrees"

    elif has_dob_unverified:
        evidence_status = "dob_unverified"

    elif records:
        evidence_status = "other_dob_status"

    elif has_qid:
        evidence_status = "qid_without_dob_status"

    else:
        evidence_status = "no_dob_evidence"

    player_status_counter[
        evidence_status
    ] += 1

    player_rows.append({
        "reep_id": reep_id,
        "label": master.get("label"),
        "status": master.get("status"),
        "gender": master.get("gender"),
        "has_qid": has_qid,
        "dob_evidence_status": evidence_status,
        "dob_agrees": has_dob_agrees,
        "dob_unverified": has_dob_unverified,
        "dob_evidence_records": len(records),
        "dob_sources": "|".join(sources),
        "dob_status_values": "|".join(dob_values),
    })


# ============================================================
# SUMMARY
# ============================================================

print("=" * 70)
print("DOB EVIDENCE SUMMARY")
print("=" * 70)

for status_name, count in sorted(
    player_status_counter.items(),
    key=lambda x: (-x[1], x[0])
):
    print(
        f"{status_name:<28} {count:>10,}"
    )

print()


# ============================================================
# WRITING CSV
# ============================================================

print("=" * 70)
print("WRITING PLAYER-LEVEL CSV")
print("=" * 70)

fieldnames = [
    "reep_id",
    "label",
    "status",
    "gender",
    "has_qid",
    "dob_evidence_status",
    "dob_agrees",
    "dob_unverified",
    "dob_evidence_records",
    "dob_sources",
    "dob_status_values",
]

with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(player_rows)

print(f"CSV written:")
print(CSV_PATH)
print()


# ============================================================
# JSON SUMMARY
# ============================================================

summary = {
    "audit": "REEP PLAYER DOB EVIDENCE AUDIT",
    "read_only": True,
    "source_database": DB_PATH,

    "players": {
        "total": total_players
    },

    "qid_evidence": {
        "players_with_qid": len(qid_players),
        "overlay_link_rows": len(overlay_player_rows)
    },

    "dob_evidence": {
        "players_with_any_dob_evidence":
            len(all_dob_evidence_players),

        "players_with_dob_agrees":
            len(dob_agrees_players),

        "players_with_dob_unverified":
            len(dob_unverified_players),

        "players_with_other_status":
            len(dob_other_players),
    },

    "dob_status_distribution":
        dict(dob_counter),

    "xid_dob_status_distribution":
        dict(xid_dob_counter),

    "confidence_distribution":
        dict(confidence_counter),

    "player_evidence_status":
        dict(player_status_counter),

    "output_files": {
        "csv": CSV_PATH,
        "json": JSON_PATH
    }
}

print("=" * 70)
print("WRITING JSON SUMMARY")
print("=" * 70)

with open(
    JSON_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        summary,
        f,
        indent=2,
        ensure_ascii=False
    )

print(f"JSON written:")
print(JSON_PATH)
print()


# ============================================================
# COMPLETE
# ============================================================

print("=" * 70)
print("DOB EVIDENCE AUDIT COMPLETE")
print("=" * 70)
print()
print(f"REEP players audited: {total_players:,}")
print(
    f"Players with any DOB evidence: "
    f"{len(all_dob_evidence_players):,}"
)
print(
    f"Players with dob-agrees evidence: "
    f"{len(dob_agrees_players):,}"
)
print(
    f"Players with dob-unverified evidence: "
    f"{len(dob_unverified_players):,}"
)
print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")
print()
print("Output files:")
print(CSV_PATH)
print(JSON_PATH)
print()

con.close()