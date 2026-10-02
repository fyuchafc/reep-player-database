import duckdb
import json
import csv
from pathlib import Path
from collections import Counter, defaultdict

# ============================================================
# REEP PLAYER QID QUALITY ANALYSIS
# ============================================================
#
# READ-ONLY AUDIT
#
# This script:
#   1. Audits QID coverage for actual REEP players
#   2. Checks QIDs per player
#   3. Checks players per QID
#   4. Checks confidence and DOB verification
#   5. Checks entity type / status / gender
#   6. Compares overlay_links QIDs with overlay_xids QIDs
#   7. Summarizes external-ID coverage
#   8. Reports shared-QID cases
#   9. Writes JSON + CSV efficiently
#
# SOURCE DATABASE IS NEVER MODIFIED.
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

# Fallback to the known absolute source path if needed
if not DB_PATH.exists():
    DB_PATH = Path(
        r"C:\Users\ADMIN\OneDrive\Documents\important database files"
        r"\fyucha-player-database-main\fyucha-player-database-main"
        r"\data\reep-register-v1.duckdb"
    )

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JSON_OUTPUT = OUTPUT_DIR / "reep-player-qid-quality.json"
CSV_OUTPUT = OUTPUT_DIR / "reep-player-qid-quality.csv"

print("=" * 70)
print("REEP PLAYER QID QUALITY ANALYSIS")
print("=" * 70)
print()
print("Source database:")
print(f"  {DB_PATH}")
print()

if not DB_PATH.exists():
    raise FileNotFoundError(f"Source database not found: {DB_PATH}")

print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=str(DB_PATH),
    read_only=True
)

print("  Database opened: READ-ONLY")
print()

# ============================================================
# VERIFY REQUIRED TABLES
# ============================================================

required_tables = {
    "players",
    "entities",
    "overlay_links",
    "overlay_xids",
}

existing_tables = {
    row[0]
    for row in con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        """
    ).fetchall()
}

missing_tables = required_tables - existing_tables

if missing_tables:
    raise RuntimeError(
        f"Missing required tables: {sorted(missing_tables)}"
    )

# ============================================================
# LOAD PLAYER MASTER
# ============================================================

print("Loading REEP player master...")

player_rows = con.execute(
    """
    SELECT
        reep_id,
        label,
        status,
        gender
    FROM main.players
    """
).fetchall()

player_count = len(player_rows)

player_info = {}

for reep_id, label, status, gender in player_rows:
    player_info[reep_id] = {
        "label": label,
        "status": status,
        "gender": gender,
    }

print(f"  Total REEP players: {player_count:,}")
print()

# ============================================================
# LOAD PLAYER QID LINKS
# ============================================================

print("Loading QID links belonging to actual REEP players...")

qid_rows = con.execute(
    """
    SELECT
        ol.reep_id,
        ol.qid,
        ol.confidence,
        ol.dob_check,
        ol.entity_type,
        ol.inherited
    FROM main.overlay_links ol
    INNER JOIN main.players p
        ON p.reep_id = ol.reep_id
    WHERE ol.entity_type = 'player'
      AND ol.qid IS NOT NULL
      AND TRIM(ol.qid) <> ''
    ORDER BY ol.reep_id, ol.qid
    """
).fetchall()

print(f"  Player QID-link rows: {len(qid_rows):,}")
print()

# ============================================================
# PLAYER QID COVERAGE
# ============================================================

players_with_qid = {row[0] for row in qid_rows}

players_without_qid = player_count - len(players_with_qid)

qid_coverage = (
    len(players_with_qid) / player_count * 100
    if player_count
    else 0
)

print("Player QID coverage:")
print(f"  Total REEP players:          {player_count:,}")
print(f"  Players with QID:            {len(players_with_qid):,}")
print(f"  Players without QID:         {players_without_qid:,}")
print(f"  QID coverage:                {qid_coverage:.2f}%")
print()

# ============================================================
# QIDS PER PLAYER
# ============================================================

qids_by_player = defaultdict(list)

for row in qid_rows:
    reep_id = row[0]
    qid = row[1]
    qids_by_player[reep_id].append(qid)

qid_count_distribution = Counter(
    len(qids)
    for qids in qids_by_player.values()
)

multiple_qid_players = [
    reep_id
    for reep_id, qids in qids_by_player.items()
    if len(set(qids)) > 1
]

print("Analyzing QIDs per player...")

for count in sorted(qid_count_distribution):
    print(
        f"  {count} QID(s) per player: "
        f"{qid_count_distribution[count]:,} players"
    )

print()
print(
    f"  Players with multiple QIDs: "
    f"{len(multiple_qid_players):,}"
)
print()

# ============================================================
# DISTINCT QIDS
# ============================================================

all_qids = {
    row[1]
    for row in qid_rows
}

print("Distinct player QIDs:")
print(f"  {len(all_qids):,}")
print()

# ============================================================
# PLAYERS PER QID
# ============================================================

players_by_qid = defaultdict(set)

for row in qid_rows:
    players_by_qid[row[1]].add(row[0])

qid_player_distribution = Counter(
    len(players)
    for players in players_by_qid.values()
)

shared_qids = {
    qid: players
    for qid, players in players_by_qid.items()
    if len(players) > 1
}

print("Analyzing players per QID...")

for count in sorted(qid_player_distribution):
    print(
        f"  {count} player(s) per QID: "
        f"{qid_player_distribution[count]:,} QIDs"
    )

print()
print(
    f"  QIDs linked to multiple players: "
    f"{len(shared_qids):,}"
)
print()

# ============================================================
# CONFIDENCE
# ============================================================

confidence_distribution = Counter(
    row[2]
    for row in qid_rows
)

print("Confidence distribution...")

for value in sorted(
    confidence_distribution,
    key=lambda x: (x is None, x)
):
    print(
        f"  {value}: "
        f"{confidence_distribution[value]:,}"
    )

print()

# ============================================================
# DOB CHECK
# ============================================================

dob_distribution = Counter(
    row[3]
    for row in qid_rows
)

print("DOB verification distribution...")

for value in sorted(
    dob_distribution,
    key=lambda x: (x is None, str(x))
):
    print(
        f"  {value}: "
        f"{dob_distribution[value]:,}"
    )

print()

# ============================================================
# ENTITY TYPE
# ============================================================

entity_type_distribution = Counter(
    row[4]
    for row in qid_rows
)

print("Entity type distribution...")

for value in sorted(entity_type_distribution):
    print(
        f"  {value}: "
        f"{entity_type_distribution[value]:,}"
    )

print()

# ============================================================
# INHERITED
# ============================================================

inherited_distribution = Counter(
    str(row[5])
    for row in qid_rows
)

print("Inherited distribution...")

for value in sorted(inherited_distribution):
    print(
        f"  {value}: "
        f"{inherited_distribution[value]:,}"
    )

print()

# ============================================================
# STATUS
# ============================================================

status_distribution = Counter(
    player_info[row[0]]["status"]
    for row in qid_rows
)

print("Player status distribution...")

for value in sorted(status_distribution):
    print(
        f"  {value}: "
        f"{status_distribution[value]:,}"
    )

print()

# ============================================================
# GENDER
# ============================================================

gender_distribution = Counter(
    player_info[row[0]]["gender"]
    for row in qid_rows
)

print("Gender distribution...")

for value in sorted(
    gender_distribution,
    key=lambda x: (x is None, str(x))
):
    print(
        f"  {value}: "
        f"{gender_distribution[value]:,}"
    )

print()

# ============================================================
# LOAD XID QID LINKS
# ============================================================

print("Analyzing QID players against external IDs...")

xid_qid_rows = con.execute(
    """
    SELECT DISTINCT
        ox.reep_id,
        ox.qid
    FROM main.overlay_xids ox
    INNER JOIN main.players p
        ON p.reep_id = ox.reep_id
    WHERE ox.qid IS NOT NULL
      AND TRIM(ox.qid) <> ''
    """
).fetchall()

xid_qid_by_player = defaultdict(set)

for reep_id, qid in xid_qid_rows:
    xid_qid_by_player[reep_id].add(qid)

qid_players_with_xid = set(xid_qid_by_player)

both_players = players_with_qid & qid_players_with_xid
qid_only_players = players_with_qid - qid_players_with_xid
xid_only_players = qid_players_with_xid - players_with_qid

print(f"  Players with QID:            {len(players_with_qid):,}")
print(f"  Players with XID:            {len(qid_players_with_xid):,}")
print(f"  Players with both:           {len(both_players):,}")
print(f"  QID-only players:            {len(qid_only_players):,}")
print(f"  XID-only players:            {len(xid_only_players):,}")
print()

# ============================================================
# QID CONSISTENCY
# ============================================================

print("Checking QID consistency between overlay_links and overlay_xids...")

xid_qid_disagreements = []

for reep_id in both_players:
    link_qids = set(qids_by_player.get(reep_id, []))
    xid_qids = set(xid_qid_by_player.get(reep_id, []))

    if not xid_qids.issubset(link_qids):
        xid_qid_disagreements.append(
            {
                "reep_id": reep_id,
                "overlay_link_qids": sorted(link_qids),
                "overlay_xid_qids": sorted(xid_qids),
            }
        )

print(
    "  Players with XID QID not present in overlay_links: "
    f"{len(xid_qid_disagreements):,}"
)
print()

# ============================================================
# EXTERNAL ID ROW COUNTS PER QID PLAYER
# ============================================================

print("Analyzing external IDs attached to QID players...")

xid_count_rows = con.execute(
    """
    SELECT
        ox.reep_id,
        COUNT(*) AS xid_rows
    FROM main.overlay_xids ox
    INNER JOIN main.players p
        ON p.reep_id = ox.reep_id
    INNER JOIN (
        SELECT DISTINCT reep_id
        FROM main.overlay_links
        WHERE entity_type = 'player'
          AND qid IS NOT NULL
          AND TRIM(qid) <> ''
    ) q
        ON q.reep_id = ox.reep_id
    GROUP BY ox.reep_id
    """
).fetchall()

xid_rows_per_player = Counter(
    count
    for _, count in xid_count_rows
)

for count in sorted(xid_rows_per_player):
    print(
        f"  {count} external ID row(s): "
        f"{xid_rows_per_player[count]:,} players"
    )

print()

# ============================================================
# PROVIDER COVERAGE
# ============================================================

print("Provider coverage among QID-linked players...")

provider_rows = con.execute(
    """
    SELECT
        ox.provider,
        COUNT(DISTINCT ox.reep_id) AS players
    FROM main.overlay_xids ox
    INNER JOIN (
        SELECT DISTINCT reep_id
        FROM main.overlay_links
        WHERE entity_type = 'player'
          AND qid IS NOT NULL
          AND TRIM(qid) <> ''
    ) q
        ON q.reep_id = ox.reep_id
    GROUP BY ox.provider
    ORDER BY players DESC, ox.provider
    """
).fetchall()

provider_coverage = {}

for provider, count in provider_rows:
    provider_coverage[provider] = count
    print(
        f"  {provider}: "
        f"{count:,} QID-linked players"
    )

print()

# ============================================================
# SHARED QID DETAILS
# ============================================================

print("Inspecting QID-only players...")
print()

print("Inspecting players with multiple QIDs...")
print()

print("Inspecting QIDs shared by multiple players...")
print()

shared_qid_details = []

for qid in sorted(shared_qids):
    print(f"  QID {qid}")

    players = sorted(shared_qids[qid])

    detail_players = []

    for reep_id in players:
        info = player_info[reep_id]

        print(
            f"    {reep_id} | "
            f"{info['label']} | "
            f"status={info['status']} | "
            f"gender={info['gender']}"
        )

        detail_players.append(
            {
                "reep_id": reep_id,
                "label": info["label"],
                "status": info["status"],
                "gender": info["gender"],
            }
        )

    shared_qid_details.append(
        {
            "qid": qid,
            "players": detail_players,
        }
    )

print()

# ============================================================
# BUILD PLAYER-LEVEL CSV DATA
# ============================================================

print("Building player-level QID quality CSV data...")

csv_rows = []

for reep_id in sorted(players_with_qid):
    info = player_info[reep_id]

    qids = sorted(set(qids_by_player.get(reep_id, [])))

    # Preserve the actual row-level QID metadata.
    matching_rows = [
        row
        for row in qid_rows
        if row[0] == reep_id
    ]

    confidence_values = sorted(
        {
            row[2]
            for row in matching_rows
        },
        key=lambda x: (x is None, x)
    )

    dob_values = sorted(
        {
            row[3]
            for row in matching_rows
        },
        key=lambda x: (x is None, str(x))
    )

    xid_qids = sorted(
        xid_qid_by_player.get(reep_id, set())
    )

    csv_rows.append(
        [
            reep_id,
            info["label"],
            info["status"],
            info["gender"],
            "|".join(qids),
            "|".join(
                "" if value is None else str(value)
                for value in confidence_values
            ),
            "|".join(
                "" if value is None else str(value)
                for value in dob_values
            ),
            "|".join(xid_qids),
            len(xid_qids),
        ]
    )

# ============================================================
# WRITE CSV EFFICIENTLY
# ============================================================

print("Writing player-level QID quality CSV...")

with CSV_OUTPUT.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:
    writer = csv.writer(f)

    writer.writerow(
        [
            "reep_id",
            "label",
            "status",
            "gender",
            "qids",
            "confidence_values",
            "dob_check_values",
            "xid_qids",
            "xid_qid_count",
        ]
    )

    writer.writerows(csv_rows)

print(f"  CSV written: {CSV_OUTPUT}")
print()

# ============================================================
# BUILD JSON SUMMARY
# ============================================================

summary = {
    "source_database": str(DB_PATH),
    "read_only": True,

    "total_players": player_count,

    "qid_coverage": {
        "players_with_qid": len(players_with_qid),
        "players_without_qid": players_without_qid,
        "percentage": round(qid_coverage, 2),
    },

    "qids_per_player": {
        str(k): v
        for k, v in sorted(qid_count_distribution.items())
    },

    "players_with_multiple_qids": len(multiple_qid_players),

    "distinct_player_qids": len(all_qids),

    "players_per_qid": {
        str(k): v
        for k, v in sorted(qid_player_distribution.items())
    },

    "shared_qids": {
        "count": len(shared_qids),
        "details": shared_qid_details,
    },

    "confidence_distribution": {
        str(k): v
        for k, v in confidence_distribution.items()
    },

    "dob_verification_distribution": {
        str(k): v
        for k, v in dob_distribution.items()
    },

    "entity_type_distribution": {
        str(k): v
        for k, v in entity_type_distribution.items()
    },

    "inherited_distribution": {
        str(k): v
        for k, v in inherited_distribution.items()
    },

    "status_distribution": {
        str(k): v
        for k, v in status_distribution.items()
    },

    "gender_distribution": {
        str(k): v
        for k, v in gender_distribution.items()
    },

    "qid_xid_consistency": {
        "players_with_qid": len(players_with_qid),
        "players_with_xid_qid": len(qid_players_with_xid),
        "players_with_both": len(both_players),
        "qid_only_players": len(qid_only_players),
        "xid_only_players": len(xid_only_players),
        "xid_qid_not_in_overlay_links": len(
            xid_qid_disagreements
        ),
    },

    "xid_rows_per_qid_linked_player": {
        str(k): v
        for k, v in sorted(xid_rows_per_player.items())
    },

    "provider_coverage": provider_coverage,

    "shared_qid_details": shared_qid_details,

    "outputs": {
        "json": str(JSON_OUTPUT),
        "csv": str(CSV_OUTPUT),
    },
}

print("Writing JSON quality summary...")

with JSON_OUTPUT.open(
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        summary,
        f,
        indent=2,
        ensure_ascii=False
    )

print(f"  JSON written: {JSON_OUTPUT}")
print()

# ============================================================
# CLOSE
# ============================================================

con.close()

print("=" * 70)
print("QID QUALITY ANALYSIS COMPLETE")
print("=" * 70)
print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")
print()
print("Output files:")
print(f"  {JSON_OUTPUT}")
print(f"  {CSV_OUTPUT}")