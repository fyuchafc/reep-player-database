import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import duckdb


# ============================================================
# REEP PLAYER EXTERNAL-ID QUALITY AUDIT
# READ-ONLY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = (
    BASE_DIR.parent
    / "fyucha-player-database-main"
    / "fyucha-player-database-main"
    / "data"
    / "reep-register-v1.duckdb"
)

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUTPUT_DIR / "reep-player-external-id-quality.csv"
JSON_PATH = OUTPUT_DIR / "reep-player-external-id-quality.json"


print("=" * 70)
print("REEP PLAYER EXTERNAL-ID QUALITY AUDIT")
print("=" * 70)
print()
print("Source database:")
print(f"  {DB_PATH}")
print()
print("Opening REEP database READ-ONLY...")

con = duckdb.connect(str(DB_PATH), read_only=True)

print("  Database opened: READ-ONLY")
print()


# ============================================================
# LOAD PLAYER MASTER
# ============================================================

print("Loading REEP player master...")

players = con.execute("""
    SELECT
        reep_id,
        status,
        label,
        gender,
        country
    FROM main.players
    ORDER BY reep_id
""").fetchall()

player_ids = {row[0] for row in players}
player_map = {row[0]: row for row in players}

print(f"  Total REEP players: {len(players):,}")
print()


# ============================================================
# LOAD EXTERNAL IDS
# ============================================================

print("Loading external-ID records...")

xids = con.execute("""
    SELECT
        reep_id,
        provider,
        property,
        external_id,
        rank,
        confidence,
        dob_check,
        qid
    FROM main.overlay_xids
""").fetchall()

print(f"  Total external-ID rows: {len(xids):,}")
print()


# ============================================================
# FILTER TO ACTUAL PLAYERS
# ============================================================

print("Checking external-ID references...")

invalid_references = [
    row
    for row in xids
    if row[0] not in player_ids
]

player_xids = [
    row
    for row in xids
    if row[0] in player_ids
]

print(
    f"  External-ID rows belonging to players: "
    f"{len(player_xids):,}"
)

print(
    f"  External-ID rows outside player master: "
    f"{len(invalid_references):,}"
)
print()


# ============================================================
# GROUP BY PLAYER
# ============================================================

xids_by_player = defaultdict(list)

for row in player_xids:
    xids_by_player[row[0]].append(row)


# ============================================================
# BASIC COVERAGE
# ============================================================

print("Analyzing external-ID coverage...")

players_with_xids = len(xids_by_player)
players_without_xids = len(players) - players_with_xids

print(f"  Total REEP players:          {len(players):,}")
print(f"  Players with external IDs:  {players_with_xids:,}")
print(f"  Players without external IDs: {players_without_xids:,}")

coverage = (
    players_with_xids / len(players) * 100
    if players
    else 0
)

print(f"  External-ID coverage:        {coverage:.2f}%")
print()


# ============================================================
# EXTERNAL IDS PER PLAYER
# ============================================================

print("Analyzing external IDs per player...")

xid_count_distribution = Counter(
    len(rows)
    for rows in xids_by_player.values()
)

for count in sorted(xid_count_distribution):
    print(
        f"  {count} external ID row(s): "
        f"{xid_count_distribution[count]:,} players"
    )

max_xids = (
    max(xid_count_distribution)
    if xid_count_distribution
    else 0
)

players_10_plus = sum(
    count
    for xid_count, count in xid_count_distribution.items()
    if xid_count >= 10
)

players_20_plus = sum(
    count
    for xid_count, count in xid_count_distribution.items()
    if xid_count >= 20
)

print()
print(f"  Maximum external IDs/player: {max_xids:,}")
print(f"  Players with 10+ IDs:        {players_10_plus:,}")
print(f"  Players with 20+ IDs:        {players_20_plus:,}")
print()


# ============================================================
# PROVIDER COVERAGE
# ============================================================

print("Analyzing provider coverage...")

provider_players = defaultdict(set)
provider_rows = Counter()

for row in player_xids:

    reep_id = row[0]
    provider = row[1]

    provider_players[provider].add(reep_id)
    provider_rows[provider] += 1

for provider in sorted(
    provider_players,
    key=lambda p: (-len(provider_players[p]), p)
):
    print(
        f"  {provider}: "
        f"{len(provider_players[provider]):,} players "
        f"/ {provider_rows[provider]:,} rows"
    )

print()


# ============================================================
# PROPERTY COVERAGE
# ============================================================

print("Analyzing provider/property coverage...")

provider_property_players = defaultdict(set)
provider_property_rows = Counter()

for row in player_xids:

    reep_id = row[0]
    provider = row[1]
    property_name = row[2]

    key = (
        provider,
        property_name
    )

    provider_property_players[key].add(reep_id)
    provider_property_rows[key] += 1

for key in sorted(
    provider_property_players,
    key=lambda k: (
        k[0],
        str(k[1])
    )
):

    provider, property_name = key

    print(
        f"  {provider} | {property_name}: "
        f"{len(provider_property_players[key]):,} players "
        f"/ {provider_property_rows[key]:,} rows"
    )

print()


# ============================================================
# NULL / EMPTY VALUES
# ============================================================

print("Checking external-ID fields...")

null_provider = sum(
    1 for row in player_xids
    if row[1] is None
)

null_property = sum(
    1 for row in player_xids
    if row[2] is None
)

null_external_id = sum(
    1 for row in player_xids
    if row[3] is None
)

empty_external_id = sum(
    1
    for row in player_xids
    if row[3] is not None
    and not str(row[3]).strip()
)

print(f"  NULL provider:     {null_provider:,}")
print(f"  NULL property:     {null_property:,}")
print(f"  NULL external ID:  {null_external_id:,}")
print(f"  Empty external ID: {empty_external_id:,}")
print()


# ============================================================
# EXACT DUPLICATE ROWS
# ============================================================

print("Checking exact duplicate external-ID rows...")

exact_counter = Counter(
    (
        row[0],
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],
        row[6],
        row[7],
    )
    for row in player_xids
)

exact_duplicate_groups = sum(
    1
    for count in exact_counter.values()
    if count > 1
)

exact_duplicate_rows = sum(
    count - 1
    for count in exact_counter.values()
    if count > 1
)

print(
    f"  Exact duplicate groups: "
    f"{exact_duplicate_groups:,}"
)

print(
    f"  Exact duplicate rows beyond first: "
    f"{exact_duplicate_rows:,}"
)
print()


# ============================================================
# UNIQUE EXTERNAL IDS
# ============================================================

print("Analyzing unique external IDs...")

provider_property_id_players = defaultdict(set)

for row in player_xids:

    key = (
        row[1],
        row[2],
        row[3],
    )

    provider_property_id_players[key].add(row[0])


unique_exact_keys = len(provider_property_id_players)

collision_groups = {
    key: ids
    for key, ids in provider_property_id_players.items()
    if len(ids) > 1
}

collision_players = {
    player_id
    for ids in collision_groups.values()
    for player_id in ids
}

print(
    f"  Distinct provider/property/ID keys: "
    f"{unique_exact_keys:,}"
)

print(
    f"  Exact collision groups: "
    f"{len(collision_groups):,}"
)

print(
    f"  Players in collision groups: "
    f"{len(collision_players):,}"
)
print()


# ============================================================
# PROVIDER + ID COLLISIONS
# PROPERTY IGNORED
# ============================================================

print("Analyzing provider + external-ID collisions...")

provider_id_players = defaultdict(set)

for row in player_xids:

    key = (
        row[1],
        row[3],
    )

    provider_id_players[key].add(row[0])


provider_id_collisions = {
    key: ids
    for key, ids in provider_id_players.items()
    if len(ids) > 1
}

print(
    f"  Provider + ID collision groups: "
    f"{len(provider_id_collisions):,}"
)
print()


# ============================================================
# QID CONSISTENCY
# ============================================================

print("Analyzing QID consistency across external-ID rows...")

player_qids = defaultdict(set)

for row in player_xids:

    reep_id = row[0]
    qid = row[7]

    if qid is not None and str(qid).strip():
        player_qids[reep_id].add(str(qid))


players_with_xid_qid = sum(
    1
    for player_id in xids_by_player
    if player_id in player_qids
    and player_qids[player_id]
)

players_with_multiple_xid_qids = {
    player_id: qids
    for player_id, qids in player_qids.items()
    if len(qids) > 1
}

print(
    f"  Players with QID on XID records: "
    f"{players_with_xid_qid:,}"
)

print(
    f"  Players with multiple XID QIDs: "
    f"{len(players_with_multiple_xid_qids):,}"
)
print()


# ============================================================
# CONFIDENCE DISTRIBUTION
# ============================================================

print("Analyzing confidence distribution...")

confidence_counter = Counter(
    row[5] if row[5] is not None else "<NULL>"
    for row in player_xids
)

for confidence, count in sorted(
    confidence_counter.items(),
    key=lambda x: str(x[0])
):
    print(f"  {confidence}: {count:,}")

print()


# ============================================================
# DOB CHECK DISTRIBUTION
# ============================================================

print("Analyzing DOB verification status...")

dob_counter = Counter(
    row[6] if row[6] is not None else "<NULL>"
    for row in player_xids
)

for dob_check, count in dob_counter.most_common():
    print(f"  {dob_check}: {count:,}")

print()


# ============================================================
# TOP PLAYERS BY EXTERNAL-ID COUNT
# ============================================================

print("Top players by external-ID count...")

top_players = sorted(
    xids_by_player.items(),
    key=lambda x: (-len(x[1]), x[0])
)[:30]

for index, (reep_id, rows) in enumerate(top_players, 1):

    label = player_map[reep_id][2]

    providers = sorted({
        row[1]
        for row in rows
        if row[1] is not None
    })

    print(
        f"  {index}. {label} "
        f"| {reep_id} "
        f"| IDs={len(rows)} "
        f"| providers={len(providers)}"
    )

print()


# ============================================================
# BUILD PLAYER-LEVEL CSV
# ============================================================

print("Building player-level external-ID quality CSV...")

csv_rows = []

for player_id, status, label, gender, country in players:

    rows = xids_by_player.get(
        player_id,
        []
    )

    providers = Counter(
        row[1]
        for row in rows
        if row[1] is not None
    )

    properties = Counter(
        (
            row[1],
            row[2]
        )
        for row in rows
        if row[1] is not None
    )

    qids = {
        str(row[7]).strip()
        for row in rows
        if row[7] is not None
        and str(row[7]).strip()
    }

    confidences = Counter(
        row[5] if row[5] is not None else "<NULL>"
        for row in rows
    )

    dob_checks = Counter(
        row[6] if row[6] is not None else "<NULL>"
        for row in rows
    )

    csv_rows.append([
        player_id,
        status,
        label,
        gender,
        country,
        len(rows),
        len({
            (
                row[1],
                row[2],
                row[3]
            )
            for row in rows
        }),
        len(providers),
        "; ".join(
            f"{provider}={count}"
            for provider, count
            in sorted(providers.items())
        ),
        "; ".join(
            f"{provider}|{property_name}={count}"
            for (
                provider,
                property_name
            ), count
            in sorted(
                properties.items(),
                key=lambda x: (
                    str(x[0][0]),
                    str(x[0][1])
                )
            )
        ),
        len(qids),
        "; ".join(
            str(key)
            + "="
            + str(value)
            for key, value
            in sorted(
                confidences.items(),
                key=lambda x: str(x[0])
            )
        ),
        "; ".join(
            f"{key}={value}"
            for key, value
            in sorted(dob_checks.items())
        ),
    ])


print("Writing player-level external-ID quality CSV...")

with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "reep_id",
        "status",
        "label",
        "gender",
        "country",
        "external_id_rows",
        "unique_provider_property_id",
        "provider_count",
        "provider_distribution",
        "provider_property_distribution",
        "qid_count_on_xids",
        "confidence_distribution",
        "dob_check_distribution",
    ])

    writer.writerows(csv_rows)

print(f"  CSV written: {CSV_PATH}")
print()


# ============================================================
# JSON SUMMARY
# ============================================================

print("Writing JSON audit summary...")

summary = {
    "source_database": str(DB_PATH),
    "audit_mode": "read-only",

    "players": {
        "total": len(players),
        "with_external_ids": players_with_xids,
        "without_external_ids": players_without_xids,
        "external_id_coverage_percent": round(
            coverage,
            2
        ),
    },

    "external_ids": {
        "total_rows": len(player_xids),
        "rows_outside_player_master": len(
            invalid_references
        ),
        "max_ids_per_player": max_xids,
        "players_with_10_plus_ids": players_10_plus,
        "players_with_20_plus_ids": players_20_plus,
        "provider_count": len(provider_players),
        "provider_rows": dict(provider_rows),
        "null_provider": null_provider,
        "null_property": null_property,
        "null_external_id": null_external_id,
        "empty_external_id": empty_external_id,
    },

    "duplicates": {
        "exact_duplicate_groups":
            exact_duplicate_groups,
        "exact_duplicate_rows_beyond_first":
            exact_duplicate_rows,
    },

    "collisions": {
        "distinct_provider_property_id_keys":
            unique_exact_keys,
        "provider_property_id_collision_groups":
            len(collision_groups),
        "players_in_exact_collision_groups":
            len(collision_players),
        "provider_id_collision_groups":
            len(provider_id_collisions),
    },

    "qid_consistency": {
        "players_with_xid_qid":
            players_with_xid_qid,
        "players_with_multiple_xid_qids":
            len(players_with_multiple_xid_qids),
    },

    "confidence_distribution": {
        str(key): value
        for key, value in confidence_counter.items()
    },

    "dob_check_distribution": {
        str(key): value
        for key, value in dob_counter.items()
    },

    "architecture_conclusion": [
        "reep_id remains the authoritative player identity.",
        "External IDs are attached evidence, not primary identity keys.",
        "Provider + property + external_id is the safest exact external-ID key.",
        "Even provider + property + external_id can have collisions and must not trigger automatic merges.",
        "All original provider, property, rank, confidence, DOB-check, and QID fields should be preserved.",
    ],
}

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

print(f"  JSON written: {JSON_PATH}")
print()


# ============================================================
# COMPLETE
# ============================================================

con.close()

print("=" * 70)
print("PLAYER EXTERNAL-ID QUALITY AUDIT COMPLETE")
print("=" * 70)
print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")
print()
print("Output files:")
print(f"  {CSV_PATH}")
print(f"  {JSON_PATH}")
print()