import csv
import json
import os
from collections import Counter, defaultdict
from datetime import datetime

import duckdb


# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\reep-player-database-main\output"
)

CSV_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-dob-conflicts.csv"
)

JSON_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-dob-conflicts.json"
)


# ============================================================
# HELPERS
# ============================================================

def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def print_header(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def get_columns(con, table_name):
    rows = con.execute(
        f"DESCRIBE {table_name}"
    ).fetchall()

    return [row[0] for row in rows]


def choose_column(columns, candidates):
    lowered = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]

    return None


# ============================================================
# START
# ============================================================

print("=" * 70)
print("REEP PLAYER DOB CONFLICT AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()
print("Source database:")
print(DB_PATH)


if not os.path.exists(DB_PATH):
    raise FileNotFoundError(
        f"Database not found:\n{DB_PATH}"
    )


os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================
# CONNECT READ-ONLY
# ============================================================

print()
print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=DB_PATH,
    read_only=True
)

print("Connected successfully.")


# ============================================================
# CHECK TABLES
# ============================================================

print_header("CHECKING REQUIRED TABLES")

tables = {
    row[0]
    for row in con.execute(
        "SHOW TABLES"
    ).fetchall()
}

required_tables = [
    "players",
    "overlay_links",
    "overlay_xids",
]

for table in required_tables:
    if table in tables:
        print(f"  {table:<18} FOUND")
    else:
        raise RuntimeError(
            f"Required table not found: {table}"
        )


# ============================================================
# PLAYER MASTER
# ============================================================

print_header("LOADING PLAYER MASTER")

player_columns = get_columns(con, "players")

print("Players table columns:")
print(", ".join(player_columns))

player_id_col = choose_column(
    player_columns,
    ["reep_id", "player_id", "id"]
)

label_col = choose_column(
    player_columns,
    ["label", "name", "player_name"]
)

status_col = choose_column(
    player_columns,
    ["status"]
)

if not player_id_col:
    raise RuntimeError(
        "Could not detect REEP player ID column."
    )

if not label_col:
    raise RuntimeError(
        "Could not detect player label column."
    )


player_rows = con.execute(
    f"""
    SELECT
        "{player_id_col}",
        "{label_col}",
        "{status_col if status_col else player_id_col}"
    FROM players
    """
).fetchall()


players = {}

for row in player_rows:
    reep_id = clean(row[0])

    if not reep_id:
        continue

    players[reep_id] = {
        "reep_id": reep_id,
        "label": clean(row[1]),
        "status": clean(row[2]) if status_col else "",
    }


print(f"Total REEP players: {len(players):,}")


# ============================================================
# OVERLAY LINKS
# ============================================================

print_header("ANALYSING QID DOB EVIDENCE")

link_columns = get_columns(
    con,
    "overlay_links"
)

print("overlay_links columns:")
print(", ".join(link_columns))

link_player_col = choose_column(
    link_columns,
    ["reep_id", "player_id", "id"]
)

qid_col = choose_column(
    link_columns,
    ["qid", "wikidata_qid"]
)

dob_check_col = choose_column(
    link_columns,
    ["dob_check", "dob_status"]
)

confidence_col = choose_column(
    link_columns,
    ["confidence"]
)

if not link_player_col:
    raise RuntimeError(
        "Could not detect player ID in overlay_links."
    )

if not dob_check_col:
    raise RuntimeError(
        "Could not detect dob_check in overlay_links."
    )


link_select = [
    f'"{link_player_col}"',
]

if qid_col:
    link_select.append(f'"{qid_col}"')
else:
    link_select.append("NULL")

link_select.append(f'"{dob_check_col}"')

if confidence_col:
    link_select.append(f'"{confidence_col}"')
else:
    link_select.append("NULL")


link_rows = con.execute(
    f"""
    SELECT
        {", ".join(link_select)}
    FROM overlay_links
    """
).fetchall()


qid_dob_by_player = defaultdict(list)

for row in link_rows:
    reep_id = clean(row[0])

    if reep_id not in players:
        continue

    qid = clean(row[1])
    dob_status = clean(row[2]).lower()

    confidence = row[3]

    qid_dob_by_player[reep_id].append(
        {
            "qid": qid,
            "dob_status": dob_status,
            "confidence": confidence,
        }
    )


print(
    f"Overlay-link rows belonging to players: "
    f"{sum(len(v) for v in qid_dob_by_player.values()):,}"
)


# ============================================================
# EXTERNAL IDS
# ============================================================

print_header("ANALYSING EXTERNAL-ID DOB EVIDENCE")

xid_columns = get_columns(
    con,
    "overlay_xids"
)

print("overlay_xids columns:")
print(", ".join(xid_columns))

xid_player_col = choose_column(
    xid_columns,
    ["reep_id", "player_id", "id"]
)

provider_col = choose_column(
    xid_columns,
    ["provider", "source"]
)

property_col = choose_column(
    xid_columns,
    ["property", "xid_property"]
)

external_id_col = choose_column(
    xid_columns,
    ["external_id", "xid", "externalid"]
)

xid_dob_col = choose_column(
    xid_columns,
    ["dob_check", "dob_status"]
)

xid_confidence_col = choose_column(
    xid_columns,
    ["confidence"]
)

xid_qid_col = choose_column(
    xid_columns,
    ["qid", "wikidata_qid"]
)

if not xid_player_col:
    raise RuntimeError(
        "Could not detect player ID in overlay_xids."
    )

if not xid_dob_col:
    raise RuntimeError(
        "Could not detect dob_check in overlay_xids."
    )


xid_select = [
    f'"{xid_player_col}"',
    f'"{provider_col}"' if provider_col else "NULL",
    f'"{property_col}"' if property_col else "NULL",
    f'"{external_id_col}"' if external_id_col else "NULL",
    f'"{xid_dob_col}"',
    f'"{xid_confidence_col}"' if xid_confidence_col else "NULL",
    f'"{xid_qid_col}"' if xid_qid_col else "NULL",
]


xid_rows = con.execute(
    f"""
    SELECT
        {", ".join(xid_select)}
    FROM overlay_xids
    """
).fetchall()


xid_dob_by_player = defaultdict(list)

for row in xid_rows:
    reep_id = clean(row[0])

    if reep_id not in players:
        continue

    xid_dob_by_player[reep_id].append(
        {
            "provider": clean(row[1]),
            "property": clean(row[2]),
            "external_id": clean(row[3]),
            "dob_status": clean(row[4]).lower(),
            "confidence": row[5],
            "qid": clean(row[6]),
        }
    )


print(
    f"External-ID rows belonging to players: "
    f"{sum(len(v) for v in xid_dob_by_player.values()):,}"
)


# ============================================================
# BUILD DOB EVIDENCE PROFILE
# ============================================================

print_header("BUILDING PLAYER DOB CONFLICT PROFILES")


profiles = {}

classification_counts = Counter()
provider_conflict_counts = Counter()
status_counts = Counter()

conflict_players = []
unverified_only_players = []
verified_players = []
no_evidence_players = []


for reep_id, player in players.items():

    qid_rows = qid_dob_by_player.get(
        reep_id,
        []
    )

    xid_rows_player = xid_dob_by_player.get(
        reep_id,
        []
    )

    all_evidence = []

    for item in qid_rows:
        all_evidence.append(
            {
                "source_type": "qid",
                "provider": "wikidata",
                "qid": item["qid"],
                "property": "",
                "external_id": "",
                "dob_status": item["dob_status"],
                "confidence": item["confidence"],
            }
        )

    for item in xid_rows_player:
        all_evidence.append(
            {
                "source_type": "external_id",
                "provider": item["provider"],
                "qid": item["qid"],
                "property": item["property"],
                "external_id": item["external_id"],
                "dob_status": item["dob_status"],
                "confidence": item["confidence"],
            }
        )

    statuses = set()

    for evidence in all_evidence:
        status = evidence["dob_status"]

        if status:
            statuses.add(status)
            status_counts[status] += 1

    has_agrees = "dob-agrees" in statuses
    has_unverified = "dob-unverified" in statuses

    providers = sorted(
        {
            e["provider"]
            for e in all_evidence
            if e["provider"]
        }
    )

    agrees_providers = sorted(
        {
            e["provider"]
            for e in all_evidence
            if e["dob_status"] == "dob-agrees"
            and e["provider"]
        }
    )

    unverified_providers = sorted(
        {
            e["provider"]
            for e in all_evidence
            if e["dob_status"] == "dob-unverified"
            and e["provider"]
        }
    )

    # --------------------------------------------------------
    # Classification
    # --------------------------------------------------------

    if not all_evidence:
        classification = "no_dob_evidence"

    elif has_agrees and has_unverified:
        classification = "mixed_dob_status"

    elif has_agrees:
        classification = "dob_agrees"

    elif has_unverified:
        classification = "dob_unverified_only"

    else:
        classification = "other"

    classification_counts[classification] += 1

    # --------------------------------------------------------
    # Conflict definition
    # --------------------------------------------------------
    #
    # A conflict exists when a player has both:
    #
    #   dob-agrees
    #   dob-unverified
    #
    # This is deliberately conservative.
    #
    # We do NOT treat multiple providers agreeing with
    # each other as a conflict.
    #
    # --------------------------------------------------------

    is_conflict = (
        has_agrees
        and has_unverified
    )

    if is_conflict:
        conflict_players.append(reep_id)

        provider_conflict_counts["mixed_status"] += 1

        if agrees_providers and unverified_providers:
            provider_conflict_counts[
                "different_provider_groups"
            ] += 1

    elif classification == "dob_unverified_only":
        unverified_only_players.append(
            reep_id
        )

    elif classification == "dob_agrees":
        verified_players.append(
            reep_id
        )

    elif classification == "no_dob_evidence":
        no_evidence_players.append(
            reep_id
        )

    profiles[reep_id] = {
        "reep_id": reep_id,
        "label": player["label"],
        "status": player["status"],
        "classification": classification,
        "is_conflict": is_conflict,
        "evidence_rows": len(all_evidence),
        "providers": providers,
        "provider_count": len(providers),
        "agrees_provider_count": len(
            agrees_providers
        ),
        "unverified_provider_count": len(
            unverified_providers
        ),
        "agrees_providers": agrees_providers,
        "unverified_providers": unverified_providers,
        "qid_evidence_count": len(qid_rows),
        "external_id_evidence_count": len(
            xid_rows_player
        ),
        "dob_agrees_count": sum(
            1
            for e in all_evidence
            if e["dob_status"] == "dob-agrees"
        ),
        "dob_unverified_count": sum(
            1
            for e in all_evidence
            if e["dob_status"] == "dob-unverified"
        ),
    }


# ============================================================
# SUMMARY
# ============================================================

print_header("DOB CONFLICT SUMMARY")

print(
    f"Total REEP players:              "
    f"{len(players):,}"
)

print(
    f"Players with DOB evidence:       "
    f"{len(players) - len(no_evidence_players):,}"
)

print(
    f"Players with dob-agrees:         "
    f"{sum(1 for p in profiles.values() if p['classification'] == 'dob_agrees'): ,}"
)

print(
    f"Players unverified-only:         "
    f"{len(unverified_only_players):,}"
)

print(
    f"Players with mixed DOB status:   "
    f"{len(conflict_players):,}"
)

print(
    f"Players with no DOB evidence:    "
    f"{len(no_evidence_players):,}"
)


# ============================================================
# CONFLICT DETAILS
# ============================================================

print_header("DOB CONFLICT PLAYERS")

if not conflict_players:
    print(
        "No players have both dob-agrees and "
        "dob-unverified evidence."
    )

else:
    print(
        f"Players with DOB conflicts: "
        f"{len(conflict_players):,}"
    )

    # Keep terminal output short.
    for reep_id in conflict_players[:50]:

        profile = profiles[reep_id]

        print()
        print(
            f"{reep_id} | "
            f"{profile['label']}"
        )

        print(
            f"  agrees evidence: "
            f"{profile['dob_agrees_count']}"
        )

        print(
            f"  unverified evidence: "
            f"{profile['dob_unverified_count']}"
        )

        print(
            f"  agrees providers: "
            f"{', '.join(profile['agrees_providers'])}"
        )

        print(
            f"  unverified providers: "
            f"{', '.join(profile['unverified_providers'])}"
        )

    if len(conflict_players) > 50:
        print()
        print(
            f"... {len(conflict_players) - 50:,} "
            f"additional conflict players written to CSV."
        )


# ============================================================
# PROVIDER SUMMARY
# ============================================================

print_header("DOB STATUS BY PROVIDER")

provider_summary = defaultdict(
    lambda: {
        "players": set(),
        "agrees": set(),
        "unverified": set(),
    }
)

for reep_id, rows in xid_dob_by_player.items():

    for row in rows:

        provider = row["provider"]

        if not provider:
            continue

        provider_summary[
            provider
        ]["players"].add(reep_id)

        if row["dob_status"] == "dob-agrees":
            provider_summary[
                provider
            ]["agrees"].add(reep_id)

        elif row["dob_status"] == "dob-unverified":
            provider_summary[
                provider
            ]["unverified"].add(reep_id)


provider_rows = []

for provider, data in provider_summary.items():

    provider_rows.append(
        {
            "provider": provider,
            "players": len(data["players"]),
            "dob_agrees": len(data["agrees"]),
            "dob_unverified": len(
                data["unverified"]
            ),
        }
    )


provider_rows.sort(
    key=lambda x: x["players"],
    reverse=True
)

for row in provider_rows[:25]:

    print(
        f"  {row['provider']:<30} "
        f"players={row['players']:>8,} | "
        f"agrees={row['dob_agrees']:>8,} | "
        f"unverified={row['dob_unverified']:>6,}"
    )


# ============================================================
# WRITE CSV
# ============================================================

print_header("WRITING PLAYER-LEVEL CSV")

csv_fields = [
    "reep_id",
    "label",
    "status",
    "classification",
    "is_conflict",
    "evidence_rows",
    "provider_count",
    "agrees_provider_count",
    "unverified_provider_count",
    "qid_evidence_count",
    "external_id_evidence_count",
    "dob_agrees_count",
    "dob_unverified_count",
    "providers",
    "agrees_providers",
    "unverified_providers",
]


with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8-sig",
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=csv_fields
    )

    writer.writeheader()

    for reep_id in sorted(profiles):

        profile = profiles[reep_id]

        row = dict(profile)

        row["is_conflict"] = (
            "yes"
            if profile["is_conflict"]
            else "no"
        )

        row["providers"] = "; ".join(
            profile["providers"]
        )

        row["agrees_providers"] = "; ".join(
            profile["agrees_providers"]
        )

        row["unverified_providers"] = "; ".join(
            profile["unverified_providers"]
        )

        writer.writerow(
            {
                field: row.get(field, "")
                for field in csv_fields
            }
        )


print(f"CSV written:\n{CSV_PATH}")


# ============================================================
# JSON SUMMARY
# ============================================================

print_header("WRITING JSON SUMMARY")

summary = {
    "audit": "REEP PLAYER DOB CONFLICT AUDIT",
    "generated_at_utc": datetime.utcnow().isoformat()
    + "Z",
    "source_database": DB_PATH,
    "read_only": True,

    "total_players": len(players),

    "players_with_dob_evidence": (
        len(players)
        - len(no_evidence_players)
    ),

    "dob_agrees_players": sum(
        1
        for p in profiles.values()
        if p["classification"] == "dob_agrees"
    ),

    "dob_unverified_only_players": len(
        unverified_only_players
    ),

    "mixed_dob_status_players": len(
        conflict_players
    ),

    "no_dob_evidence_players": len(
        no_evidence_players
    ),

    "classification_counts": dict(
        classification_counts
    ),

    "status_counts": dict(
        status_counts
    ),

    "conflict_summary": {
        "mixed_status_players": len(
            conflict_players
        ),
        "different_provider_groups": provider_conflict_counts.get(
            "different_provider_groups",
            0
        ),
    },

    "provider_summary": provider_rows,

    "output_csv": CSV_PATH,
    "output_json": JSON_PATH,
}


with open(
    JSON_PATH,
    "w",
    encoding="utf-8",
) as f:

    json.dump(
        summary,
        f,
        indent=2,
        ensure_ascii=False,
    )


print(f"JSON written:\n{JSON_PATH}")


# ============================================================
# FINISH
# ============================================================

con.close()

print()
print("=" * 70)
print("DOB CONFLICT AUDIT COMPLETE")
print("=" * 70)
print()
print(
    f"REEP players audited:             "
    f"{len(players):,}"
)
print(
    f"DOB conflict players:             "
    f"{len(conflict_players):,}"
)
print(
    f"DOB unverified-only players:      "
    f"{len(unverified_only_players):,}"
)
print(
    f"No DOB evidence:                  "
    f"{len(no_evidence_players):,}"
)
print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")
print()
print("Output files:")
print(CSV_PATH)
print(JSON_PATH)
print()