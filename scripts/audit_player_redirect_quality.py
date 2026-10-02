import duckdb
import json
import csv
from pathlib import Path
from collections import Counter, defaultdict


# ============================================================
# REEP PLAYER REDIRECT / MERGE QUALITY AUDIT
# ============================================================
#
# READ-ONLY
#
# This audit does NOT:
# - modify the REEP database
# - merge players
# - delete players
# - change redirects
# - change QIDs
# - change external IDs
#
# It analyzes player redirects and the identity evidence attached
# to redirect endpoints.
#
# ============================================================


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = (
    BASE_DIR.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

# Fallback to the known absolute source location if necessary.
if not DB_PATH.exists():
    DB_PATH = Path(
        r"C:\Users\ADMIN\OneDrive\Documents\important database files"
        r"\fyucha-player-database-main\fyucha-player-database-main"
        r"\data\reep-register-v1.duckdb"
    )

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUTPUT_DIR / "reep-player-redirect-quality.csv"
JSON_PATH = OUTPUT_DIR / "reep-player-redirect-quality.json"


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def normalize_label(value):
    if value is None:
        return None

    value = str(value).strip().lower()

    if not value:
        return None

    return " ".join(value.split())


def safe_ratio(numerator, denominator):
    if denominator == 0:
        return 0.0

    return round((numerator / denominator) * 100, 2)


def print_section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ------------------------------------------------------------
# START
# ------------------------------------------------------------

print("=" * 70)
print("REEP PLAYER REDIRECT / MERGE QUALITY AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()

print("Database:")
print(DB_PATH)

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"REEP database not found:\n{DB_PATH}"
    )

print()
print("Connecting to REEP database...")

con = duckdb.connect(
    str(DB_PATH),
    read_only=True
)

print("Connected successfully.")


# ============================================================
# LOAD PLAYER MASTER
# ============================================================

print_section("LOADING PLAYER MASTER")

player_rows = con.execute(
    """
    SELECT
        reep_id,
        status,
        label,
        gender,
        country
    FROM main.players
    """
).fetchall()

players = {}

for row in player_rows:
    reep_id, status, label, gender, country = row

    players[reep_id] = {
        "reep_id": reep_id,
        "status": status,
        "label": label,
        "gender": gender,
        "country": country,
    }

print(f"REEP players loaded: {len(players):,}")


# ============================================================
# LOAD PLAYER REDIRECTS
# ============================================================

print_section("LOADING PLAYER REDIRECTS")

redirect_rows = con.execute(
    """
    SELECT
        from_id,
        to_id,
        reason
    FROM main.redirects
    """
).fetchall()

all_redirect_rows = len(redirect_rows)

player_redirects = []

for from_id, to_id, reason in redirect_rows:

    from_is_player = from_id in players
    to_is_player = to_id in players

    # Keep redirects where either endpoint is a player.
    # This lets us identify malformed or incomplete player redirects.
    if from_is_player or to_is_player:
        player_redirects.append(
            {
                "from_id": from_id,
                "to_id": to_id,
                "reason": reason,
                "from_is_player": from_is_player,
                "to_is_player": to_is_player,
            }
        )

print(f"All redirect rows: {all_redirect_rows:,}")
print(f"Redirect rows involving players: {len(player_redirects):,}")


# ============================================================
# BASIC REDIRECT COUNTS
# ============================================================

print_section("BASIC REDIRECT COUNTS")

player_only_redirects = [
    r
    for r in player_redirects
    if r["from_is_player"] and r["to_is_player"]
]

sources = [r["from_id"] for r in player_only_redirects]
targets = [r["to_id"] for r in player_only_redirects]

unique_sources = set(sources)
unique_targets = set(targets)

print(f"Player → player redirect rows: {len(player_only_redirects):,}")
print(f"Unique redirect sources: {len(unique_sources):,}")
print(f"Unique redirect targets: {len(unique_targets):,}")

sources_missing_from_players = sum(
    1 for r in player_redirects
    if not r["from_is_player"]
)

targets_missing_from_players = sum(
    1 for r in player_redirects
    if not r["to_is_player"]
)

print(
    f"Sources missing from player master: "
    f"{sources_missing_from_players:,}"
)

print(
    f"Targets missing from player master: "
    f"{targets_missing_from_players:,}"
)


# ============================================================
# REDIRECT REASON
# ============================================================

print_section("REDIRECT REASONS")

reason_counts = Counter(
    r["reason"]
    for r in player_only_redirects
)

for reason, count in sorted(
    reason_counts.items(),
    key=lambda x: (-x[1], str(x[0]))
):
    print(f"{reason}: {count:,}")


# ============================================================
# SOURCE STATUS
# ============================================================

print_section("SOURCE STATUS")

source_status_counts = Counter()

for source_id in unique_sources:
    source = players.get(source_id)

    if source:
        source_status_counts[source["status"]] += 1
    else:
        source_status_counts["MISSING"] += 1

for status, count in sorted(source_status_counts.items()):
    print(f"{status}: {count:,}")


# ============================================================
# TARGET STATUS
# ============================================================

print_section("TARGET STATUS")

target_status_counts = Counter()

for target_id in unique_targets:
    target = players.get(target_id)

    if target:
        target_status_counts[target["status"]] += 1
    else:
        target_status_counts["MISSING"] += 1

for status, count in sorted(target_status_counts.items()):
    print(f"{status}: {count:,}")


# ============================================================
# SELF REDIRECTS
# ============================================================

print_section("SELF REDIRECTS")

self_redirects = [
    r
    for r in player_only_redirects
    if r["from_id"] == r["to_id"]
]

print(f"Self redirects: {len(self_redirects):,}")


# ============================================================
# TARGET FAN-IN
# ============================================================

print_section("TARGET FAN-IN")

target_sources = defaultdict(list)

for r in player_only_redirects:
    target_sources[r["to_id"]].append(r["from_id"])

multi_source_targets = {
    target: source_list
    for target, source_list in target_sources.items()
    if len(source_list) > 1
}

print(
    f"Targets with multiple redirect sources: "
    f"{len(multi_source_targets):,}"
)

max_sources = 0
max_source_target = None

for target, source_list in target_sources.items():

    if len(source_list) > max_sources:
        max_sources = len(source_list)
        max_source_target = target

print(f"Maximum sources for one target: {max_sources:,}")

if max_source_target:
    print(f"Target with maximum sources: {max_source_target}")


# ============================================================
# REDIRECT CHAINS
# ============================================================

print_section("REDIRECT CHAINS")

redirect_map = {}

for r in player_only_redirects:
    redirect_map[r["from_id"]] = r["to_id"]

chains = []

for source_id, target_id in redirect_map.items():

    if target_id in redirect_map:
        chains.append(
            (source_id, target_id, redirect_map[target_id])
        )

print(f"Redirect chains detected: {len(chains):,}")


# ============================================================
# CYCLES
# ============================================================

print_section("REDIRECT CYCLES")

cycles = []

for source_id, target_id in redirect_map.items():

    if target_id in redirect_map:
        if redirect_map[target_id] == source_id:
            cycles.append(
                (source_id, target_id)
            )

print(f"Two-node redirect cycles: {len(cycles):,}")


# ============================================================
# LABEL COMPARISON
# ============================================================

print_section("SOURCE → TARGET LABEL COMPARISON")

same_label = 0
different_label = 0
null_label_involvement = 0

for r in player_only_redirects:

    source = players.get(r["from_id"])
    target = players.get(r["to_id"])

    if not source or not target:
        continue

    source_label = normalize_label(source["label"])
    target_label = normalize_label(target["label"])

    if source_label is None or target_label is None:
        null_label_involvement += 1

    elif source_label == target_label:
        same_label += 1

    else:
        different_label += 1

print(f"Same normalized label: {same_label:,}")
print(f"Different normalized label: {different_label:,}")
print(f"NULL label involvement: {null_label_involvement:,}")


# ============================================================
# LOAD QID EVIDENCE
# ============================================================

print_section("LOADING QID EVIDENCE")

qid_rows = con.execute(
    """
    SELECT
        reep_id,
        qid,
        confidence,
        dob_check
    FROM main.overlay_links
    WHERE qid IS NOT NULL
      AND TRIM(CAST(qid AS VARCHAR)) <> ''
    """
).fetchall()

player_qids = defaultdict(list)

for reep_id, qid, confidence, dob_check in qid_rows:

    if reep_id in players:
        player_qids[reep_id].append(
            {
                "qid": qid,
                "confidence": confidence,
                "dob_check": dob_check,
            }
        )

print(f"Player QID rows loaded: {sum(len(v) for v in player_qids.values()):,}")
print(f"Players with QID evidence: {len(player_qids):,}")


# ============================================================
# REDIRECT QID COMPARISON
# ============================================================

print_section("REDIRECT QID RELATIONSHIP")

both_qid = 0
same_qid = 0
different_qid = 0
source_only_qid = 0
target_only_qid = 0
missing_qid = 0

for r in player_only_redirects:

    source_qids = {
        item["qid"]
        for item in player_qids.get(r["from_id"], [])
    }

    target_qids = {
        item["qid"]
        for item in player_qids.get(r["to_id"], [])
    }

    if source_qids and target_qids:

        both_qid += 1

        if source_qids & target_qids:
            same_qid += 1
        else:
            different_qid += 1

    elif source_qids:
        source_only_qid += 1

    elif target_qids:
        target_only_qid += 1

    else:
        missing_qid += 1

print(f"Both endpoints have QID: {both_qid:,}")
print(f"Same QID: {same_qid:,}")
print(f"Different QID: {different_qid:,}")
print(f"Source only has QID: {source_only_qid:,}")
print(f"Target only has QID: {target_only_qid:,}")
print(f"Neither endpoint has QID: {missing_qid:,}")


# ============================================================
# LOAD EXTERNAL-ID EVIDENCE
# ============================================================

print_section("LOADING EXTERNAL-ID EVIDENCE")

xid_rows = con.execute(
    """
    SELECT
        reep_id,
        provider,
        property,
        external_id
    FROM main.overlay_xids
    WHERE provider IS NOT NULL
      AND property IS NOT NULL
      AND external_id IS NOT NULL
      AND TRIM(CAST(external_id AS VARCHAR)) <> ''
    """
).fetchall()

player_xids = defaultdict(set)

for reep_id, provider, prop, external_id in xid_rows:

    if reep_id in players:
        key = (
            str(provider),
            str(prop),
            str(external_id),
        )

        player_xids[reep_id].add(key)

print(
    f"Player external-ID rows loaded: "
    f"{sum(len(v) for v in player_xids.values()):,}"
)

print(
    f"Players with external-ID evidence: "
    f"{len(player_xids):,}"
)


# ============================================================
# REDIRECT EXTERNAL-ID COMPARISON
# ============================================================

print_section("REDIRECT EXTERNAL-ID RELATIONSHIP")

shared_xid = 0
source_only_xid = 0
target_only_xid = 0
neither_xid = 0

for r in player_only_redirects:

    source_ids = player_xids.get(r["from_id"], set())
    target_ids = player_xids.get(r["to_id"], set())

    if source_ids and target_ids:

        if source_ids & target_ids:
            shared_xid += 1

    elif source_ids:
        source_only_xid += 1

    elif target_ids:
        target_only_xid += 1

    else:
        neither_xid += 1

print(f"Redirects sharing exact provider/property/ID: {shared_xid:,}")
print(f"Source only has external IDs: {source_only_xid:,}")
print(f"Target only has external IDs: {target_only_xid:,}")
print(f"Neither endpoint has external IDs: {neither_xid:,}")


# ============================================================
# BUILD PLAYER-LEVEL REDIRECT QUALITY RECORDS
# ============================================================

print_section("BUILDING PLAYER-LEVEL REDIRECT QUALITY")

quality_records = []

for r in player_only_redirects:

    source_id = r["from_id"]
    target_id = r["to_id"]

    source = players.get(source_id)
    target = players.get(target_id)

    source_qids = sorted({
        str(item["qid"])
        for item in player_qids.get(source_id, [])
    })

    target_qids = sorted({
        str(item["qid"])
        for item in player_qids.get(target_id, [])
    })

    source_xids = player_xids.get(source_id, set())
    target_xids = player_xids.get(target_id, set())

    source_label = source["label"] if source else None
    target_label = target["label"] if target else None

    source_norm = normalize_label(source_label)
    target_norm = normalize_label(target_label)

    if source_norm is None or target_norm is None:
        label_relation = "null_label"
    elif source_norm == target_norm:
        label_relation = "same_label"
    else:
        label_relation = "different_label"

    if source_qids and target_qids:
        if set(source_qids) & set(target_qids):
            qid_relation = "same_qid"
        else:
            qid_relation = "different_qid"
    elif source_qids:
        qid_relation = "source_only"
    elif target_qids:
        qid_relation = "target_only"
    else:
        qid_relation = "neither"

    if source_xids and target_xids:

        shared = source_xids & target_xids

        if shared:
            xid_relation = "shared_exact_xid"
        else:
            xid_relation = "both_different_xids"

    elif source_xids:
        xid_relation = "source_only"

    elif target_xids:
        xid_relation = "target_only"

    else:
        xid_relation = "neither"

    quality_records.append(
        {
            "source_id": source_id,
            "target_id": target_id,
            "reason": r["reason"],
            "source_status": source["status"] if source else None,
            "target_status": target["status"] if target else None,
            "source_label": source_label,
            "target_label": target_label,
            "label_relation": label_relation,
            "source_qid_count": len(source_qids),
            "target_qid_count": len(target_qids),
            "source_qids": "|".join(source_qids),
            "target_qids": "|".join(target_qids),
            "qid_relation": qid_relation,
            "source_xid_count": len(source_xids),
            "target_xid_count": len(target_xids),
            "xid_relation": xid_relation,
            "shared_exact_xid_count": len(
                source_xids & target_xids
            ),
        }
    )


# ============================================================
# WRITE CSV
# ============================================================

print_section("WRITING CSV")

if quality_records:

    fieldnames = list(quality_records[0].keys())

    with CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(quality_records)

else:

    CSV_PATH.write_text(
        "",
        encoding="utf-8"
    )

print(f"CSV written:")
print(CSV_PATH)


# ============================================================
# SUMMARY JSON
# ============================================================

print_section("BUILDING SUMMARY JSON")

summary = {
    "audit": "reep-player-redirect-quality",
    "read_only": True,
    "source_database": str(DB_PATH),

    "player_master": {
        "total_players": len(players)
    },

    "redirects": {
        "all_redirect_rows": all_redirect_rows,
        "player_related_redirect_rows": len(player_redirects),
        "player_to_player_redirect_rows": len(player_only_redirects),
        "unique_sources": len(unique_sources),
        "unique_targets": len(unique_targets),
        "sources_missing_from_players": sources_missing_from_players,
        "targets_missing_from_players": targets_missing_from_players,
        "self_redirects": len(self_redirects),
        "redirect_chains": len(chains),
        "two_node_cycles": len(cycles),
    },

    "reasons": dict(reason_counts),

    "source_status": dict(source_status_counts),

    "target_status": dict(target_status_counts),

    "target_fan_in": {
        "targets_with_multiple_sources": len(
            multi_source_targets
        ),
        "maximum_sources_for_one_target": max_sources,
        "target_with_maximum_sources": max_source_target,
    },

    "label_relationship": {
        "same_normalized_label": same_label,
        "different_normalized_label": different_label,
        "null_label_involvement": null_label_involvement,
    },

    "qid_relationship": {
        "both_endpoints_have_qid": both_qid,
        "same_qid": same_qid,
        "different_qid": different_qid,
        "source_only_qid": source_only_qid,
        "target_only_qid": target_only_qid,
        "neither_endpoint_qid": missing_qid,
    },

    "external_id_relationship": {
        "shared_exact_provider_property_id": shared_xid,
        "source_only_external_id": source_only_xid,
        "target_only_external_id": target_only_xid,
        "neither_endpoint_external_id": neither_xid,
    },

    "quality_record_count": len(quality_records),

    "outputs": {
        "csv": str(CSV_PATH),
        "json": str(JSON_PATH),
    },
}


with JSON_PATH.open(
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


# ============================================================
# FINAL SUMMARY
# ============================================================

print()
print("=" * 70)
print("REDIRECT QUALITY AUDIT COMPLETE")
print("=" * 70)

print()
print(f"REEP players: {len(players):,}")
print(f"Player redirects: {len(player_only_redirects):,}")
print(f"Unique sources: {len(unique_sources):,}")
print(f"Unique targets: {len(unique_targets):,}")

print()
print(f"Self redirects: {len(self_redirects):,}")
print(f"Redirect chains: {len(chains):,}")
print(f"Two-node cycles: {len(cycles):,}")

print()
print(f"Same-label redirects: {same_label:,}")
print(f"Different-label redirects: {different_label:,}")

print()
print(f"Both endpoints with QID: {both_qid:,}")
print(f"Same QID: {same_qid:,}")
print(f"Different QID: {different_qid:,}")

print()
print(
    "Shared exact external IDs: "
    f"{shared_xid:,}"
)

print()
print("OUTPUT FILES")
print("-" * 70)
print(CSV_PATH)
print(JSON_PATH)

print()
print("Source database was opened READ-ONLY.")
print("No REEP source data was modified.")

con.close()