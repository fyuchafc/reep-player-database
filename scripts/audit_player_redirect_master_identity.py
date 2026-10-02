import duckdb
import json
import csv
from pathlib import Path
from collections import Counter, defaultdict

# ============================================================
# REEP PLAYER REDIRECT → MASTER IDENTITY AUDIT
# CORRECTED VERSION
#
# READ-ONLY
# Does not modify the REEP source database.
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DB_PATH = (
    BASE_DIR.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

# Fallback to the known absolute source location if necessary
if not DB_PATH.exists():
    DB_PATH = Path(
        r"C:\Users\ADMIN\OneDrive\Documents\important database files"
        r"\fyucha-player-database-main\fyucha-player-database-main"
        r"\data\reep-register-v1.duckdb"
    )

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

JSON_PATH = OUTPUT_DIR / "reep-player-redirect-master-identity-audit.json"
CSV_PATH = OUTPUT_DIR / "reep-player-redirect-master-identity.csv"


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


section("REEP PLAYER REDIRECT → MASTER IDENTITY AUDIT")

if DB_PATH.exists():
    size = DB_PATH.stat().st_size
    print(
        f"\nFile size: {size:,} bytes "
        f"({size / (1024 * 1024):.2f} MiB)"
    )
else:
    print("\nERROR: Source database not found:")
    print(DB_PATH)
    raise SystemExit(1)

print("\nOPENING DATABASE READ-ONLY...")

con = duckdb.connect(
    database=str(DB_PATH),
    read_only=True
)

section("VERIFYING REQUIRED TABLES")

required_tables = {
    "players",
    "redirects",
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

missing_tables = sorted(required_tables - existing_tables)

if missing_tables:
    print("Missing required tables:")
    for table in missing_tables:
        print(f"  - {table}")
    con.close()
    raise SystemExit(1)

print("All required tables found.")


# ============================================================
# MASTER PLAYER POPULATION
# ============================================================

section("READING MASTER PLAYER POPULATION")

players = {}

rows = con.execute(
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

for reep_id, status, label, gender, country in rows:
    players[reep_id] = {
        "reep_id": reep_id,
        "status": status,
        "label": label,
        "gender": gender,
        "country": country,
    }

print(f"Total REEP players:        {len(players):,}")
print(f"Unique REEP player IDs:    {len(players):,}")


# ============================================================
# PLAYER REDIRECTS
# ============================================================

section("LOADING PLAYER REDIRECTS")

redirect_rows = con.execute(
    """
    SELECT
        r.from_id,
        r.to_id,
        r.reason
    FROM main.redirects r
    INNER JOIN main.entities e
        ON e.reep_id = r.from_id
       AND e.entity_type = 'player'
    """
).fetchall()

print(f"Player redirect rows:       {len(redirect_rows):,}")

unique_sources = {r[0] for r in redirect_rows}
unique_targets = {r[1] for r in redirect_rows}

print(f"Unique redirect sources:   {len(unique_sources):,}")
print(f"Unique redirect targets:   {len(unique_targets):,}")


# ============================================================
# SOURCE VALIDATION
# ============================================================

section("CHECKING REDIRECT SOURCES")

missing_sources = sorted(
    source
    for source in unique_sources
    if source not in players
)

print(f"Sources missing from players: {len(missing_sources):,}")


# ============================================================
# TARGET VALIDATION
# ============================================================

section("CHECKING REDIRECT TARGETS")

targets_present = sorted(
    target
    for target in unique_targets
    if target in players
)

targets_missing = sorted(
    target
    for target in unique_targets
    if target not in players
)

print(f"Targets present in players: {len(targets_present):,}")
print(f"Targets missing from players: {len(targets_missing):,}")


# ============================================================
# REASON DISTRIBUTION
#
# IMPORTANT:
# Count redirect ROWS directly.
# Never join this calculation to one-to-many tables.
# ============================================================

section("REDIRECT REASON DISTRIBUTION")

reason_counts = Counter(
    reason for _, _, reason in redirect_rows
)

for reason, count in sorted(reason_counts.items()):
    print(f"{reason:<24} {count:,}")


# ============================================================
# SOURCE STATUS
# ============================================================

section("REDIRECT SOURCE STATUS")

source_status_counts = Counter()

for source in unique_sources:
    if source in players:
        source_status_counts[players[source]["status"]] += 1

for status, count in sorted(source_status_counts.items()):
    print(f"{status:<20} {count:,}")


# ============================================================
# TARGET STATUS
#
# Count UNIQUE TARGETS, not redirect rows.
# This avoids inflation when multiple sources point to one target.
# ============================================================

section("REDIRECT TARGET STATUS")

target_status_counts = Counter()

for target in unique_targets:
    if target in players:
        target_status_counts[players[target]["status"]] += 1

for status, count in sorted(target_status_counts.items()):
    print(f"{status:<20} {count:,}")


# ============================================================
# SELF REDIRECTS
# ============================================================

section("CHECKING SELF REDIRECTS")

self_redirects = [
    (source, target)
    for source, target, reason in redirect_rows
    if source == target
]

print(f"Self redirects: {len(self_redirects):,}")


# ============================================================
# REDIRECT CHAINS
#
# A chain exists if a redirect target is itself a redirect source.
# ============================================================

section("CHECKING REDIRECT CHAINS")

source_set = unique_sources

redirect_chains = [
    (source, target)
    for source, target, reason in redirect_rows
    if target in source_set
]

print(f"Redirect chains: {len(redirect_chains):,}")


# ============================================================
# MULTIPLE SOURCES PER TARGET
# ============================================================

section("CHECKING MULTIPLE SOURCES PER TARGET")

target_sources = defaultdict(list)

for source, target, reason in redirect_rows:
    target_sources[target].append(source)

multi_source_targets = {
    target: sources
    for target, sources in target_sources.items()
    if len(sources) > 1
}

print(f"Targets with multiple sources: {len(multi_source_targets):,}")


# ============================================================
# LABEL COMPARISON
# ============================================================

section("CHECKING SOURCE/TARGET LABELS")

same_label = 0
different_label = 0
null_label = 0

for source, target, reason in redirect_rows:

    source_record = players.get(source)
    target_record = players.get(target)

    if source_record is None or target_record is None:
        continue

    source_label = source_record["label"]
    target_label = target_record["label"]

    if source_label is None or target_label is None:
        null_label += 1
    elif source_label == target_label:
        same_label += 1
    else:
        different_label += 1

print(f"Same label:             {same_label:,}")
print(f"Different label:        {different_label:,}")
print(f"NULL label involvement: {null_label:,}")


# ============================================================
# QID DATA
#
# IMPORTANT:
# Use DISTINCT REEP/QID pairs first.
# This prevents overlay joins from multiplying redirect rows.
# ============================================================

section("LOADING PLAYER QID DATA")

qid_rows = con.execute(
    """
    SELECT DISTINCT
        reep_id,
        qid
    FROM main.overlay_links
    WHERE qid IS NOT NULL
      AND TRIM(qid) <> ''
    """
).fetchall()

player_qids = defaultdict(set)

for reep_id, qid in qid_rows:
    if reep_id in players:
        player_qids[reep_id].add(qid)

print(f"Player/QID pairs loaded: {len(qid_rows):,}")
print(f"Players with QIDs:        {len(player_qids):,}")


# ============================================================
# REDIRECT QID RELATIONSHIPS
# ============================================================

section("CHECKING REDIRECT QID RELATIONSHIPS")

both_have_qid = 0
same_qid = 0
different_qid = 0
missing_qid = 0

qid_relationship_details = []

for source, target, reason in redirect_rows:

    source_qids = player_qids.get(source, set())
    target_qids = player_qids.get(target, set())

    if source_qids and target_qids:
        both_have_qid += 1

        if source_qids & target_qids:
            same_qid += 1
        else:
            different_qid += 1

    else:
        missing_qid += 1

    qid_relationship_details.append(
        {
            "source_qids": sorted(source_qids),
            "target_qids": sorted(target_qids),
        }
    )

print(f"Both have QID:     {both_have_qid:,}")
print(f"Same QID:          {same_qid:,}")
print(f"Different QID:     {different_qid:,}")
print(f"Missing QID:       {missing_qid:,}")


# ============================================================
# EXACT EXTERNAL-ID SHARING
#
# Identity key:
# provider + property + external_id
# ============================================================

section("LOADING PLAYER EXTERNAL IDs")

xid_rows = con.execute(
    """
    SELECT DISTINCT
        reep_id,
        provider,
        property,
        external_id
    FROM main.overlay_xids
    WHERE external_id IS NOT NULL
      AND TRIM(external_id) <> ''
    """
).fetchall()

player_xids = defaultdict(set)

for reep_id, provider, prop, external_id in xid_rows:

    if reep_id not in players:
        continue

    key = (
        str(provider),
        str(prop),
        str(external_id),
    )

    player_xids[reep_id].add(key)

print(f"Player/XID identity rows loaded: {len(xid_rows):,}")


section("CHECKING EXACT EXTERNAL-ID SHARING")

shared_external_id = 0
shared_external_details = []

for source, target, reason in redirect_rows:

    source_xids = player_xids.get(source, set())
    target_xids = player_xids.get(target, set())

    shared = source_xids & target_xids

    if shared:
        shared_external_id += 1

        shared_external_details.append(
            {
                "source": source,
                "target": target,
                "shared_ids": sorted(
                    [
                        {
                            "provider": x[0],
                            "property": x[1],
                            "external_id": x[2],
                        }
                        for x in shared
                    ],
                    key=lambda x: (
                        x["provider"],
                        x["property"],
                        x["external_id"],
                    ),
                ),
            }
        )

print(
    f"Redirects sharing an exact external ID: "
    f"{shared_external_id:,}"
)


# ============================================================
# STATUS TRANSITIONS
# ============================================================

section("SOURCE → TARGET STATUS TRANSITIONS")

transition_counts = Counter()

for source, target, reason in redirect_rows:

    source_record = players.get(source)
    target_record = players.get(target)

    if source_record is None or target_record is None:
        continue

    transition = (
        source_record["status"],
        target_record["status"],
    )

    transition_counts[transition] += 1

for (source_status, target_status), count in sorted(
    transition_counts.items()
):
    print(
        f"{source_status} -> {target_status}: "
        f"{count:,}"
    )


# ============================================================
# BUILD DETAIL
# ============================================================

section("BUILDING REDIRECT DETAIL")

details = []

for index, (source, target, reason) in enumerate(
    redirect_rows
):

    source_record = players.get(source)
    target_record = players.get(target)

    source_qids = sorted(player_qids.get(source, set()))
    target_qids = sorted(player_qids.get(target, set()))

    shared_xids = player_xids.get(source, set()) & \
        player_xids.get(target, set())

    detail = {
        "source_reep_id": source,
        "target_reep_id": target,
        "reason": reason,

        "source_present_in_players":
            source_record is not None,

        "target_present_in_players":
            target_record is not None,

        "source_status":
            source_record["status"]
            if source_record else None,

        "target_status":
            target_record["status"]
            if target_record else None,

        "source_label":
            source_record["label"]
            if source_record else None,

        "target_label":
            target_record["label"]
            if target_record else None,

        "same_label":
            (
                source_record is not None
                and target_record is not None
                and source_record["label"] is not None
                and target_record["label"] is not None
                and source_record["label"]
                == target_record["label"]
            ),

        "source_qids": source_qids,
        "target_qids": target_qids,

        "qid_relationship":
            (
                "both_missing"
                if not source_qids and not target_qids
                else
                "source_missing"
                if not source_qids
                else
                "target_missing"
                if not target_qids
                else
                "same_qid"
                if set(source_qids) & set(target_qids)
                else
                "different_qid"
            ),

        "shared_external_ids": [
            {
                "provider": x[0],
                "property": x[1],
                "external_id": x[2],
            }
            for x in sorted(
                shared_xids,
                key=lambda x: (
                    x[0],
                    x[1],
                    x[2],
                ),
            )
        ],
    }

    details.append(detail)


# ============================================================
# MULTI-SOURCE TARGET SAMPLES
# ============================================================

section("MULTI-SOURCE TARGET SAMPLES")

sample_count = 0

for target, sources in sorted(
    multi_source_targets.items()
):

    if sample_count >= 10:
        break

    target_record = players.get(target)

    if target_record is None:
        continue

    print()
    print(
        f"Target: {target} | "
        f"{target_record['label']} | "
        f"sources={len(sources)}"
    )

    for source in sources:

        source_record = players.get(source)

        if source_record:
            source_label = source_record["label"]
            source_status = source_record["status"]
        else:
            source_label = None
            source_status = None

        reason = next(
            r
            for s, t, r in redirect_rows
            if s == source and t == target
        )

        print(
            f"  <- {source} | "
            f"{source_label} | "
            f"{source_status} | "
            f"{reason}"
        )

    sample_count += 1


# ============================================================
# AUDIT SUMMARY
# ============================================================

audit = {
    "database": {
        "path": str(DB_PATH),
        "size_bytes": DB_PATH.stat().st_size,
        "size_mib": round(
            DB_PATH.stat().st_size / (1024 * 1024),
            2,
        ),
        "read_only": True,
    },

    "master_players": {
        "total_players": len(players),
        "unique_player_ids": len(players),
    },

    "redirects": {
        "player_redirect_rows": len(redirect_rows),
        "unique_sources": len(unique_sources),
        "unique_targets": len(unique_targets),

        "sources_missing_from_players":
            len(missing_sources),

        "targets_present_in_players":
            len(targets_present),

        "targets_missing_from_players":
            len(targets_missing),

        "reason_distribution":
            dict(sorted(reason_counts.items())),

        "source_status_distribution":
            dict(sorted(source_status_counts.items())),

        "target_status_distribution":
            dict(sorted(target_status_counts.items())),

        "self_redirects":
            len(self_redirects),

        "redirect_chains":
            len(redirect_chains),

        "targets_with_multiple_sources":
            len(multi_source_targets),

        "same_label":
            same_label,

        "different_label":
            different_label,

        "null_label_involvement":
            null_label,

        "qid_relationships": {
            "both_have_qid": both_have_qid,
            "same_qid": same_qid,
            "different_qid": different_qid,
            "missing_qid": missing_qid,
        },

        "shared_exact_external_id":
            shared_external_id,

        "status_transitions": {
            f"{source_status}->{target_status}":
                count
            for (source_status, target_status), count
            in sorted(transition_counts.items())
        },
    },

    "multi_source_targets": [
        {
            "target_reep_id": target,
            "target_label":
                players[target]["label"]
                if target in players else None,
            "source_count": len(sources),
            "sources": sources,
        }
        for target, sources
        in sorted(multi_source_targets.items())
    ],

    "missing_target_ids": targets_missing,

    "redirect_details": details,
}


# ============================================================
# WRITE JSON
# ============================================================

section("WRITING JSON AUDIT")

with JSON_PATH.open(
    "w",
    encoding="utf-8"
) as f:
    json.dump(
        audit,
        f,
        indent=2,
        ensure_ascii=False,
    )


# ============================================================
# WRITE CSV
# ============================================================

section("WRITING CSV AUDIT")

csv_fields = [
    "source_reep_id",
    "target_reep_id",
    "reason",
    "source_present_in_players",
    "target_present_in_players",
    "source_status",
    "target_status",
    "source_label",
    "target_label",
    "same_label",
    "source_qids",
    "target_qids",
    "qid_relationship",
    "shared_external_ids",
]

with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline=""
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=csv_fields,
    )

    writer.writeheader()

    for row in details:

        csv_row = dict(row)

        csv_row["source_qids"] = ";".join(
            row["source_qids"]
        )

        csv_row["target_qids"] = ";".join(
            row["target_qids"]
        )

        csv_row["shared_external_ids"] = json.dumps(
            row["shared_external_ids"],
            ensure_ascii=False,
        )

        writer.writerow(csv_row)


# ============================================================
# COMPLETE
# ============================================================

section("AUDIT COMPLETE")

print()
print("JSON output:")
print(JSON_PATH)

print()
print("CSV output:")
print(CSV_PATH)

print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")

con.close()