import duckdb
import csv
import json
from pathlib import Path
from collections import defaultdict, Counter


# ======================================================================
# REEP PLAYER IDENTITY EVIDENCE AUDIT
# ======================================================================

print("=" * 70)
print("REEP PLAYER IDENTITY EVIDENCE AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()


# ======================================================================
# PATHS
# ======================================================================

DB_PATH = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"reep-player-database-main\output"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_PATH = OUTPUT_DIR / "reep-player-identity-evidence.csv"
JSON_PATH = OUTPUT_DIR / "reep-player-identity-evidence.json"


# ======================================================================
# HELPERS
# ======================================================================

def table_exists(con, table_name):
    rows = con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = ?
        """,
        [table_name]
    ).fetchall()

    return len(rows) > 0


def get_columns(con, table_name):
    rows = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ?
        ORDER BY ordinal_position
        """,
        [table_name]
    ).fetchall()

    return [r[0] for r in rows]


def pick_column(columns, candidates):
    lowered = {c.lower(): c for c in columns}

    for candidate in candidates:
        if candidate.lower() in lowered:
            return lowered[candidate.lower()]

    return None


def pct(value, total):
    if total == 0:
        return 0.0
    return round((value / total) * 100, 2)


# ======================================================================
# OPEN DATABASE
# ======================================================================

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Database not found:\n{DB_PATH}"
    )

print("Source database:")
print(f"  {DB_PATH}")
print()

print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=str(DB_PATH),
    read_only=True
)

print("Connected successfully.")
print()


# ======================================================================
# REQUIRED TABLES
# ======================================================================

required_tables = [
    "players",
    "entities",
    "overlay_links",
    "overlay_xids",
    "aliases",
    "overlay_aliases",
]

print("=" * 70)
print("CHECKING REQUIRED TABLES")
print("=" * 70)

for table in required_tables:
    if table_exists(con, table):
        print(f"  {table:<20} FOUND")
    else:
        print(f"  {table:<20} MISSING")

print()


# ======================================================================
# LOAD PLAYER MASTER
# ======================================================================

print("=" * 70)
print("LOADING PLAYER MASTER")
print("=" * 70)

player_columns = get_columns(con, "players")

print("Players table columns:")
print("  " + ", ".join(player_columns))
print()

player_id_col = pick_column(
    player_columns,
    ["reep_id", "id", "entity_id"]
)

label_col = pick_column(
    player_columns,
    ["label", "name"]
)

status_col = pick_column(
    player_columns,
    ["status"]
)

gender_col = pick_column(
    player_columns,
    ["gender", "sex"]
)

country_col = pick_column(
    player_columns,
    ["country", "nationality"]
)

if not player_id_col:
    raise RuntimeError("Could not detect player ID column.")

if not label_col:
    raise RuntimeError("Could not detect player label column.")

print("Detected columns:")
print(f"  Player ID: {player_id_col}")
print(f"  Label:     {label_col}")
print(f"  Status:    {status_col}")
print(f"  Gender:    {gender_col}")
print(f"  Country:   {country_col}")
print()

select_fields = [
    f'"{player_id_col}" AS reep_id',
    f'"{label_col}" AS label',
]

if status_col:
    select_fields.append(f'"{status_col}" AS status')
else:
    select_fields.append("NULL AS status")

if gender_col:
    select_fields.append(f'"{gender_col}" AS gender')
else:
    select_fields.append("NULL AS gender")

if country_col:
    select_fields.append(f'"{country_col}" AS country')
else:
    select_fields.append("NULL AS country")

players = con.execute(
    f"""
    SELECT
        {", ".join(select_fields)}
    FROM players
    ORDER BY "{player_id_col}"
    """
).fetchall()

total_players = len(players)

print(f"Total REEP players: {total_players:,}")
print()


# ======================================================================
# PLAYER DICTIONARY
# ======================================================================

player_data = {}

for row in players:
    reep_id = row[0]

    player_data[reep_id] = {
        "reep_id": reep_id,
        "label": row[1],
        "status": row[2],
        "gender": row[3],
        "country": row[4],

        "qid_count": 0,
        "qid": None,
        "qid_conflict": False,

        "external_id_count": 0,
        "provider_count": 0,
        "providers": set(),
        "external_id_collision": False,

        "alias_count": 0,
        "overlay_alias_count": 0,

        "redirect": False,

        "has_gender": row[3] is not None and str(row[3]).strip() != "",
        "has_country": row[4] is not None and str(row[4]).strip() != "",

        "evidence_profile": "none",
    }


# ======================================================================
# GENDER / COUNTRY / STATUS COUNTS
# ======================================================================

gender_counts = Counter()
status_counts = Counter()

for p in player_data.values():
    gender = p["gender"]

    if gender is None or str(gender).strip() == "":
        gender_counts["NULL"] += 1
    else:
        gender_counts[str(gender)] += 1

    status = p["status"]

    if status is None or str(status).strip() == "":
        status_counts["NULL"] += 1
    else:
        status_counts[str(status)] += 1


# ======================================================================
# QID EVIDENCE
# ======================================================================

print("=" * 70)
print("QID EVIDENCE")
print("=" * 70)

overlay_link_columns = get_columns(con, "overlay_links")

print(
    "overlay_links columns:"
)
print("  " + ", ".join(overlay_link_columns))
print()

qid_player_col = pick_column(
    overlay_link_columns,
    ["reep_id", "player_id", "entity_id"]
)

qid_col = pick_column(
    overlay_link_columns,
    ["qid", "wikidata_id"]
)

qid_confidence_col = pick_column(
    overlay_link_columns,
    ["confidence", "link_confidence"]
)

qid_dob_col = pick_column(
    overlay_link_columns,
    ["dob_check", "dob_verification"]
)

qid_entity_col = pick_column(
    overlay_link_columns,
    ["entity_type", "type"]
)

if qid_player_col and qid_col:
    qid_fields = [
        f'"{qid_player_col}" AS reep_id',
        f'"{qid_col}" AS qid',
    ]

    if qid_confidence_col:
        qid_fields.append(
            f'"{qid_confidence_col}" AS confidence'
        )
    else:
        qid_fields.append("NULL AS confidence")

    if qid_dob_col:
        qid_fields.append(
            f'"{qid_dob_col}" AS dob_check'
        )
    else:
        qid_fields.append("NULL AS dob_check")

    if qid_entity_col:
        qid_fields.append(
            f'"{qid_entity_col}" AS entity_type'
        )
    else:
        qid_fields.append("NULL AS entity_type")

    qid_rows = con.execute(
        f"""
        SELECT
            {", ".join(qid_fields)}
        FROM overlay_links
        WHERE "{qid_player_col}" IN (
            SELECT "{player_id_col}"
            FROM players
        )
        """
    ).fetchall()

else:
    qid_rows = []

print(f"QID rows belonging to REEP players: {len(qid_rows):,}")

qid_by_player = defaultdict(set)
qid_confidence = defaultdict(list)
qid_dob = defaultdict(list)

for row in qid_rows:
    reep_id = row[0]
    qid = row[1]

    if reep_id not in player_data:
        continue

    if qid is not None and str(qid).strip():
        qid_by_player[reep_id].add(str(qid).strip())

    if row[2] is not None:
        qid_confidence[reep_id].append(row[2])

    if row[3] is not None:
        qid_dob[reep_id].append(str(row[3]))

for reep_id, qids in qid_by_player.items():
    p = player_data[reep_id]

    p["qid_count"] = len(qids)

    if len(qids) == 1:
        p["qid"] = next(iter(qids))

    elif len(qids) > 1:
        p["qid_conflict"] = True

players_with_qid = len(qid_by_player)
players_multiple_qids = sum(
    1 for qids in qid_by_player.values()
    if len(qids) > 1
)

distinct_qids = len(
    set(
        qid
        for qids in qid_by_player.values()
        for qid in qids
    )
)

print(f"Players with QID: {players_with_qid:,}")
print(f"Players with multiple QIDs: {players_multiple_qids:,}")
print(f"Distinct QIDs: {distinct_qids:,}")
print()


# ======================================================================
# QID SHARED BY MULTIPLE PLAYERS
# ======================================================================

qid_to_players = defaultdict(set)

for reep_id, qids in qid_by_player.items():
    for qid in qids:
        qid_to_players[qid].add(reep_id)

shared_qids = {
    qid: ids
    for qid, ids in qid_to_players.items()
    if len(ids) > 1
}

players_in_shared_qid_groups = len(
    set(
        reep_id
        for ids in shared_qids.values()
        for reep_id in ids
    )
)

print("QID sharing:")
print(f"  QIDs linked to multiple players: {len(shared_qids):,}")
print(
    f"  Players involved in shared-QID groups: "
    f"{players_in_shared_qid_groups:,}"
)
print()


# ======================================================================
# EXTERNAL-ID EVIDENCE
# ======================================================================

print("=" * 70)
print("EXTERNAL-ID EVIDENCE")
print("=" * 70)

xid_columns = get_columns(con, "overlay_xids")

print("overlay_xids columns:")
print("  " + ", ".join(xid_columns))
print()

xid_player_col = pick_column(
    xid_columns,
    ["reep_id", "player_id", "entity_id"]
)

xid_provider_col = pick_column(
    xid_columns,
    ["provider", "source"]
)

xid_property_col = pick_column(
    xid_columns,
    ["property"]
)

xid_external_col = pick_column(
    xid_columns,
    ["external_id", "externalid", "id"]
)

if xid_player_col:
    xid_fields = [
        f'"{xid_player_col}" AS reep_id'
    ]

    if xid_provider_col:
        xid_fields.append(
            f'"{xid_provider_col}" AS provider'
        )
    else:
        xid_fields.append("NULL AS provider")

    if xid_property_col:
        xid_fields.append(
            f'"{xid_property_col}" AS property'
        )
    else:
        xid_fields.append("NULL AS property")

    if xid_external_col:
        xid_fields.append(
            f'"{xid_external_col}" AS external_id'
        )
    else:
        xid_fields.append("NULL AS external_id")

    xid_rows = con.execute(
        f"""
        SELECT
            {", ".join(xid_fields)}
        FROM overlay_xids
        WHERE "{xid_player_col}" IN (
            SELECT "{player_id_col}"
            FROM players
        )
        """
    ).fetchall()

else:
    xid_rows = []

print(
    f"External-ID rows belonging to REEP players: "
    f"{len(xid_rows):,}"
)

xid_by_player = defaultdict(int)
providers_by_player = defaultdict(set)
xid_keys_by_player = defaultdict(set)

for row in xid_rows:
    reep_id = row[0]

    if reep_id not in player_data:
        continue

    xid_by_player[reep_id] += 1

    provider = row[1]

    if provider is not None and str(provider).strip():
        providers_by_player[reep_id].add(
            str(provider).strip()
        )

    provider_value = (
        str(row[1]).strip()
        if row[1] is not None
        else ""
    )

    property_value = (
        str(row[2]).strip()
        if row[2] is not None
        else ""
    )

    external_value = (
        str(row[3]).strip()
        if row[3] is not None
        else ""
    )

    if external_value:
        xid_key = (
            provider_value,
            property_value,
            external_value
        )

        xid_keys_by_player[reep_id].add(xid_key)


for reep_id, count in xid_by_player.items():
    player_data[reep_id]["external_id_count"] = count

for reep_id, providers in providers_by_player.items():
    player_data[reep_id]["providers"] = providers
    player_data[reep_id]["provider_count"] = len(providers)


# ======================================================================
# EXTERNAL-ID COLLISIONS
# ======================================================================

xid_key_players = defaultdict(set)

for reep_id, keys in xid_keys_by_player.items():
    for key in keys:
        xid_key_players[key].add(reep_id)

collision_keys = {
    key: ids
    for key, ids in xid_key_players.items()
    if len(ids) > 1
}

players_in_xid_collision = set()

for ids in collision_keys.values():
    players_in_xid_collision.update(ids)

for reep_id in players_in_xid_collision:
    player_data[reep_id]["external_id_collision"] = True

print(
    f"Exact provider/property/ID collision groups: "
    f"{len(collision_keys):,}"
)

print(
    f"Players in exact collision groups: "
    f"{len(players_in_xid_collision):,}"
)

print()


# ======================================================================
# ALIAS EVIDENCE
# ======================================================================

print("=" * 70)
print("ALIAS EVIDENCE")
print("=" * 70)

alias_columns = get_columns(con, "aliases")

print("aliases columns:")
print("  " + ", ".join(alias_columns))
print()

alias_player_col = pick_column(
    alias_columns,
    ["reep_id", "player_id", "entity_id"]
)

if alias_player_col:
    alias_rows = con.execute(
        f"""
        SELECT "{alias_player_col}" AS reep_id
        FROM aliases
        WHERE "{alias_player_col}" IN (
            SELECT "{player_id_col}"
            FROM players
        )
        """
    ).fetchall()
else:
    alias_rows = []

alias_by_player = Counter()

for row in alias_rows:
    reep_id = row[0]

    if reep_id in player_data:
        alias_by_player[reep_id] += 1

for reep_id, count in alias_by_player.items():
    player_data[reep_id]["alias_count"] = count

players_with_aliases = len(alias_by_player)

print(f"Alias rows belonging to players: {len(alias_rows):,}")
print(f"Players with aliases: {players_with_aliases:,}")
print()


# ======================================================================
# OVERLAY ALIAS EVIDENCE
# ======================================================================

print("=" * 70)
print("OVERLAY ALIAS EVIDENCE")
print("=" * 70)

overlay_alias_columns = get_columns(
    con,
    "overlay_aliases"
)

print("overlay_aliases columns:")
print("  " + ", ".join(overlay_alias_columns))
print()

overlay_alias_player_col = pick_column(
    overlay_alias_columns,
    ["reep_id", "player_id", "entity_id"]
)

overlay_alias_source_col = pick_column(
    overlay_alias_columns,
    ["source", "name_source"]
)

if overlay_alias_player_col:
    overlay_alias_fields = [
        f'"{overlay_alias_player_col}" AS reep_id'
    ]

    if overlay_alias_source_col:
        overlay_alias_fields.append(
            f'"{overlay_alias_source_col}" AS source'
        )
    else:
        overlay_alias_fields.append(
            "NULL AS source"
        )

    overlay_alias_rows = con.execute(
        f"""
        SELECT
            {", ".join(overlay_alias_fields)}
        FROM overlay_aliases
        WHERE "{overlay_alias_player_col}" IN (
            SELECT "{player_id_col}"
            FROM players
        )
        """
    ).fetchall()

else:
    overlay_alias_rows = []

overlay_alias_by_player = Counter()
overlay_alias_sources = Counter()

for row in overlay_alias_rows:
    reep_id = row[0]

    if reep_id in player_data:
        overlay_alias_by_player[reep_id] += 1

    if row[1] is not None:
        overlay_alias_sources[str(row[1])] += 1

for reep_id, count in overlay_alias_by_player.items():
    player_data[reep_id]["overlay_alias_count"] = count

players_with_overlay_aliases = len(
    overlay_alias_by_player
)

print(
    f"Overlay alias rows belonging to players: "
    f"{len(overlay_alias_rows):,}"
)

print(
    f"Players with overlay aliases: "
    f"{players_with_overlay_aliases:,}"
)

print("Overlay alias sources:")

for source, count in overlay_alias_sources.most_common():
    print(f"  {source}: {count:,}")

print()


# ======================================================================
# REDIRECT EVIDENCE
# ======================================================================

print("=" * 70)
print("REDIRECT EVIDENCE")
print("=" * 70)

redirect_detected = 0

if table_exists(con, "redirects"):

    redirect_columns = get_columns(
        con,
        "redirects"
    )

    print("redirects columns:")
    print("  " + ", ".join(redirect_columns))
    print()

    redirect_source_col = pick_column(
        redirect_columns,
        ["source", "source_id", "from_id", "reep_id"]
    )

    redirect_target_col = pick_column(
        redirect_columns,
        ["target", "target_id", "to_id"]
    )

    if redirect_source_col:
        if redirect_target_col:
            redirect_rows = con.execute(
                f"""
                SELECT
                    "{redirect_source_col}",
                    "{redirect_target_col}"
                FROM redirects
                """
            ).fetchall()
        else:
            redirect_rows = con.execute(
                f"""
                SELECT "{redirect_source_col}"
                FROM redirects
                """
            ).fetchall()

        for row in redirect_rows:

            source_id = row[0]

            if source_id in player_data:
                player_data[source_id]["redirect"] = True
                redirect_detected += 1

            if redirect_target_col and len(row) > 1:
                target_id = row[1]

                if target_id in player_data:
                    pass

print(
    f"Player redirect sources detected: "
    f"{redirect_detected:,}"
)

print()


# ======================================================================
# BUILD EVIDENCE PROFILES
# ======================================================================

print("=" * 70)
print("BUILDING PLAYER EVIDENCE PROFILES")
print("=" * 70)

profile_counts = Counter()

for p in player_data.values():

    has_qid = p["qid_count"] > 0
    has_xid = p["external_id_count"] > 0
    has_alias = p["alias_count"] > 0
    has_overlay_alias = p["overlay_alias_count"] > 0
    has_gender = p["has_gender"]
    has_country = p["has_country"]

    pathways = sum([
        has_qid,
        has_xid,
        has_alias,
        has_overlay_alias,
        has_gender,
        has_country,
    ])

    # The profile describes available evidence.
    # It does NOT claim that the identity is verified.
    if pathways == 0:
        profile = "none"

    elif has_qid and has_xid and has_alias:
        profile = "qid_xid_alias"

    elif has_qid and has_xid:
        profile = "qid_xid"

    elif has_qid and has_alias:
        profile = "qid_alias"

    elif has_xid and has_alias:
        profile = "xid_alias"

    elif has_qid:
        profile = "qid_only"

    elif has_xid:
        profile = "xid_only"

    elif has_alias:
        profile = "alias_only"

    elif has_gender:
        profile = "gender_only"

    else:
        profile = "other"

    p["evidence_profile"] = profile
    profile_counts[profile] += 1


# ======================================================================
# COVERAGE SUMMARY
# ======================================================================

players_with_xid = len(xid_by_player)

players_with_any_indirect = sum(
    1
    for p in player_data.values()
    if (
        p["qid_count"] > 0
        or p["external_id_count"] > 0
        or p["alias_count"] > 0
        or p["overlay_alias_count"] > 0
    )
)

players_with_no_indirect = (
    total_players - players_with_any_indirect
)


# ======================================================================
# PRINT COMPACT SUMMARY
# ======================================================================

print()
print("=" * 70)
print("IDENTITY EVIDENCE SUMMARY")
print("=" * 70)

print()
print(f"Total REEP players:              {total_players:,}")

print()
print("DIRECT MASTER FIELDS")
print("-" * 70)
print(
    f"Gender present:                  "
    f"{sum(1 for p in player_data.values() if p['has_gender']):,}"
)
print(
    f"Country present:                 "
    f"{sum(1 for p in player_data.values() if p['has_country']):,}"
)

print()
print("QID EVIDENCE")
print("-" * 70)
print(f"Players with QID:                {players_with_qid:,}")
print(f"Players with multiple QIDs:      {players_multiple_qids:,}")
print(f"Shared QID groups:                {len(shared_qids):,}")

print()
print("EXTERNAL-ID EVIDENCE")
print("-" * 70)
print(f"Players with external IDs:       {players_with_xid:,}")
print(f"Exact collision groups:           {len(collision_keys):,}")
print(
    f"Players in collision groups:     "
    f"{len(players_in_xid_collision):,}"
)

print()
print("ALIAS EVIDENCE")
print("-" * 70)
print(f"Players with aliases:             {players_with_aliases:,}")
print(
    f"Players with overlay aliases:     "
    f"{players_with_overlay_aliases:,}"
)

print()
print("INDIRECT IDENTITY PATHWAY")
print("-" * 70)
print(
    f"Players with any indirect path:  "
    f"{players_with_any_indirect:,}"
)
print(
    f"Players with no indirect path:   "
    f"{players_with_no_indirect:,}"
)
print(
    f"Indirect pathway coverage:       "
    f"{pct(players_with_any_indirect, total_players):.2f}%"
)

print()
print("EVIDENCE PROFILES")
print("-" * 70)

for profile, count in profile_counts.most_common():
    print(
        f"{profile:<25} "
        f"{count:>10,} "
        f"({pct(count, total_players):>6.2f}%)"
    )

print()


# ======================================================================
# BUILD CSV
# ======================================================================

print("=" * 70)
print("WRITING PLAYER-LEVEL CSV")
print("=" * 70)

csv_fields = [
    "reep_id",
    "label",
    "status",
    "gender",
    "country",
    "has_gender",
    "has_country",
    "qid_count",
    "qid",
    "qid_conflict",
    "external_id_count",
    "provider_count",
    "providers",
    "external_id_collision",
    "alias_count",
    "overlay_alias_count",
    "redirect",
    "evidence_profile",
]

with CSV_PATH.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=csv_fields
    )

    writer.writeheader()

    for reep_id in sorted(player_data):

        p = player_data[reep_id]

        writer.writerow({
            "reep_id": p["reep_id"],
            "label": p["label"],
            "status": p["status"],
            "gender": p["gender"],
            "country": p["country"],
            "has_gender": p["has_gender"],
            "has_country": p["has_country"],
            "qid_count": p["qid_count"],
            "qid": p["qid"],
            "qid_conflict": p["qid_conflict"],
            "external_id_count": p["external_id_count"],
            "provider_count": p["provider_count"],
            "providers": ";".join(
                sorted(p["providers"])
            ),
            "external_id_collision": p[
                "external_id_collision"
            ],
            "alias_count": p["alias_count"],
            "overlay_alias_count": p[
                "overlay_alias_count"
            ],
            "redirect": p["redirect"],
            "evidence_profile": p[
                "evidence_profile"
            ],
        })

print(f"CSV written:")
print(f"  {CSV_PATH}")
print()


# ======================================================================
# JSON SUMMARY
# ======================================================================

print("=" * 70)
print("WRITING JSON SUMMARY")
print("=" * 70)

json_summary = {
    "audit": "REEP PLAYER IDENTITY EVIDENCE AUDIT",
    "read_only": True,

    "database": str(DB_PATH),

    "players": {
        "total": total_players,
    },

    "gender": {
        "present": sum(
            1
            for p in player_data.values()
            if p["has_gender"]
        ),
        "missing": sum(
            1
            for p in player_data.values()
            if not p["has_gender"]
        ),
    },

    "country": {
        "present": sum(
            1
            for p in player_data.values()
            if p["has_country"]
        ),
        "missing": sum(
            1
            for p in player_data.values()
            if not p["has_country"]
        ),
    },

    "qid": {
        "players_with_qid": players_with_qid,
        "players_multiple_qids": players_multiple_qids,
        "distinct_qids": distinct_qids,
        "shared_qids": len(shared_qids),
        "players_in_shared_qid_groups":
            players_in_shared_qid_groups,
    },

    "external_ids": {
        "players_with_external_ids":
            players_with_xid,
        "exact_collision_groups":
            len(collision_keys),
        "players_in_collision_groups":
            len(players_in_xid_collision),
    },

    "aliases": {
        "players_with_aliases":
            players_with_aliases,
        "players_with_overlay_aliases":
            players_with_overlay_aliases,
    },

    "indirect_pathways": {
        "players_with_any_indirect_path":
            players_with_any_indirect,
        "players_with_no_indirect_path":
            players_with_no_indirect,
        "coverage_percent":
            pct(
                players_with_any_indirect,
                total_players
            ),
    },

    "status_distribution":
        dict(status_counts),

    "gender_distribution":
        dict(gender_counts),

    "evidence_profiles":
        dict(profile_counts),

    "output_files": {
        "csv": str(CSV_PATH),
        "json": str(JSON_PATH),
    },
}

with JSON_PATH.open(
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        json_summary,
        f,
        indent=2,
        ensure_ascii=False
    )

print(f"JSON written:")
print(f"  {JSON_PATH}")
print()


# ======================================================================
# COMPLETE
# ======================================================================

print("=" * 70)
print("PLAYER IDENTITY EVIDENCE AUDIT COMPLETE")
print("=" * 70)
print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")
print()
print("Output files:")
print(f"  {CSV_PATH}")
print(f"  {JSON_PATH}")
print()
print("No REEP source data was modified.")
print()

con.close()