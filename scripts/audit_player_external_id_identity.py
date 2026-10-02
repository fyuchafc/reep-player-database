import csv
import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime, timezone

import duckdb


# ======================================================================
# REEP PLAYER EXTERNAL-ID IDENTITY AUDIT
# ======================================================================

print("=" * 70)
print("REEP PLAYER EXTERNAL-ID IDENTITY AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()


# ======================================================================
# PATHS
# ======================================================================

DB_PATH = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\reep-player-database-main\output"
)

PLAYER_CSV = os.path.join(
    OUTPUT_DIR,
    "reep-player-external-id-identity.csv"
)

GROUP_CSV = os.path.join(
    OUTPUT_DIR,
    "reep-external-id-identity-groups.csv"
)

JSON_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "reep-player-external-id-identity.json"
)


# ======================================================================
# HELPERS
# ======================================================================

def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    # Remove accents where possible.
    import unicodedata

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )

    # Keep letters and numbers only.
    value = re.sub(r"[^a-z0-9]+", "", value)

    return value


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def pct(part, total):
    if not total:
        return 0.0

    return round((part / total) * 100, 2)


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ======================================================================
# DATABASE CHECK
# ======================================================================

if not os.path.exists(DB_PATH):
    raise FileNotFoundError(
        f"Database not found:\n{DB_PATH}"
    )

ensure_output_dir()

print("Source database:")
print(f"  {DB_PATH}")
print()

print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=DB_PATH,
    read_only=True
)

print("Connected successfully.")
print()


# ======================================================================
# CHECK TABLES
# ======================================================================

print("=" * 70)
print("CHECKING REQUIRED TABLES")
print("=" * 70)

tables = {
    row[0]
    for row in con.execute(
        "SHOW TABLES"
    ).fetchall()
}

required = [
    "players",
    "overlay_xids",
]

for table in required:
    if table in tables:
        print(f"  {table:<20} FOUND")
    else:
        raise RuntimeError(
            f"Required table missing: {table}"
        )

print()


# ======================================================================
# PLAYER MASTER
# ======================================================================

print("=" * 70)
print("LOADING PLAYER MASTER")
print("=" * 70)

player_columns = [
    row[0]
    for row in con.execute(
        "DESCRIBE players"
    ).fetchall()
]

print("Players table columns:")
print("  " + ", ".join(player_columns))
print()

required_player_columns = [
    "reep_id",
    "label",
    "status",
    "gender",
]

for column in required_player_columns:
    if column not in player_columns:
        raise RuntimeError(
            f"Required players column missing: {column}"
        )


players = con.execute(
    """
    SELECT
        reep_id,
        label,
        status,
        gender
    FROM players
    """
).fetchall()

print(f"Total REEP players: {len(players):,}")
print()


player_map = {}

for reep_id, label, status, gender in players:
    player_map[str(reep_id)] = {
        "reep_id": str(reep_id),
        "label": clean(label),
        "status": clean(status),
        "gender": clean(gender),
    }


# ======================================================================
# LOAD EXTERNAL IDs
# ======================================================================

print("=" * 70)
print("LOADING PLAYER-LINKED EXTERNAL IDs")
print("=" * 70)

xid_columns = [
    row[0]
    for row in con.execute(
        "DESCRIBE overlay_xids"
    ).fetchall()
]

print("overlay_xids columns:")
print("  " + ", ".join(xid_columns))
print()

required_xid_columns = [
    "reep_id",
    "provider",
    "property",
    "external_id",
]

for column in required_xid_columns:
    if column not in xid_columns:
        raise RuntimeError(
            f"Required overlay_xids column missing: {column}"
        )


xid_rows = con.execute(
    """
    SELECT
        reep_id,
        provider,
        property,
        external_id,
        rank,
        confidence,
        dob_check,
        qid
    FROM overlay_xids
    WHERE reep_id IS NOT NULL
    """
).fetchall()

print(
    f"External-ID rows belonging to REEP players: "
    f"{len(xid_rows):,}"
)
print()


# ======================================================================
# BUILD GROUPS
# ======================================================================

print("=" * 70)
print("BUILDING PROVIDER + EXTERNAL-ID GROUPS")
print("=" * 70)

groups = defaultdict(list)

for row in xid_rows:

    (
        reep_id,
        provider,
        property_name,
        external_id,
        rank,
        confidence,
        dob_check,
        qid,
    ) = row

    reep_id = str(reep_id)

    if reep_id not in player_map:
        continue

    provider = clean(provider)
    property_name = clean(property_name)
    external_id = clean(external_id)

    if not provider or not external_id:
        continue

    key = (
        provider,
        external_id,
    )

    groups[key].append({
        "reep_id": reep_id,
        "provider": provider,
        "property": property_name,
        "external_id": external_id,
        "rank": rank,
        "confidence": confidence,
        "dob_check": clean(dob_check),
        "qid": clean(qid),
    })


# Only groups involving more than one player are identity conflicts.
conflict_groups = {}

for key, rows in groups.items():

    unique_players = {
        row["reep_id"]
        for row in rows
    }

    if len(unique_players) > 1:
        conflict_groups[key] = rows


print(
    f"Provider + external-ID groups: "
    f"{len(groups):,}"
)

print(
    f"Identity conflict groups: "
    f"{len(conflict_groups):,}"
)

print()


# ======================================================================
# ANALYZE CONFLICT GROUPS
# ======================================================================

print("=" * 70)
print("ANALYZING IDENTITY CONFLICT GROUPS")
print("=" * 70)

group_records = []
player_conflicts = defaultdict(list)

same_name_groups = 0
different_name_groups = 0

same_gender_groups = 0
different_gender_groups = 0

shared_qid_groups = 0
different_qid_groups = 0
missing_qid_groups = 0

same_dob_groups = 0
mixed_dob_groups = 0

exact_provider_property_groups = 0


for group_number, (key, rows) in enumerate(
    conflict_groups.items(),
    start=1
):

    provider, external_id = key

    unique_players = sorted(
        {
            row["reep_id"]
            for row in rows
        }
    )

    labels = []
    normalized_labels = set()
    genders = set()
    qids = set()
    dob_statuses = set()
    properties = set()

    for reep_id in unique_players:

        player = player_map[reep_id]

        label = player["label"]
        gender = player["gender"]

        labels.append(label)

        normalized_labels.add(
            normalize_text(label)
        )

        if gender:
            genders.add(
                gender.lower()
            )

    for row in rows:

        qid = clean(row["qid"])
        dob_status = clean(row["dob_check"])
        property_name = clean(row["property"])

        if qid:
            qids.add(qid)

        if dob_status:
            dob_statuses.add(
                dob_status.lower()
            )

        if property_name:
            properties.add(property_name)

    # --------------------------------------------------------------
    # NAME
    # --------------------------------------------------------------

    if len(normalized_labels) == 1:
        name_relation = "same_normalized_label"
        same_name_groups += 1
    else:
        name_relation = "different_normalized_label"
        different_name_groups += 1

    # --------------------------------------------------------------
    # GENDER
    # --------------------------------------------------------------

    if len(genders) <= 1:
        gender_relation = "same_or_missing_gender"
        same_gender_groups += 1
    else:
        gender_relation = "different_gender"
        different_gender_groups += 1

    # --------------------------------------------------------------
    # QID
    # --------------------------------------------------------------

    if len(qids) == 0:
        qid_relation = "no_qid"
        missing_qid_groups += 1

    elif len(qids) == 1:
        qid_relation = "shared_qid"
        shared_qid_groups += 1

    else:
        qid_relation = "different_qids"
        different_qid_groups += 1

    # --------------------------------------------------------------
    # DOB
    # --------------------------------------------------------------

    if len(dob_statuses) <= 1:
        dob_relation = "same_dob_status"
        same_dob_groups += 1
    else:
        dob_relation = "mixed_dob_status"
        mixed_dob_groups += 1

    # --------------------------------------------------------------
    # EXACT PROPERTY COLLISION
    # --------------------------------------------------------------

    if len(properties) == 1:
        exact_provider_property_groups += 1

    record = {
        "group_id": group_number,
        "provider": provider,
        "external_id": external_id,
        "players": unique_players,
        "player_count": len(unique_players),
        "labels": labels,
        "name_relation": name_relation,
        "gender_relation": gender_relation,
        "qid_relation": qid_relation,
        "dob_relation": dob_relation,
        "properties": sorted(properties),
        "rows": rows,
    }

    group_records.append(record)

    for reep_id in unique_players:
        player_conflicts[reep_id].append(
            record
        )


# ======================================================================
# PLAYER-LEVEL PROFILE
# ======================================================================

print("=" * 70)
print("BUILDING PLAYER-LEVEL IDENTITY PROFILES")
print("=" * 70)

player_records = []

for reep_id, player in player_map.items():

    conflicts = player_conflicts.get(
        reep_id,
        []
    )

    conflict_count = len(conflicts)

    providers = set()
    external_ids = set()
    group_ids = []

    name_conflict = False
    gender_conflict = False
    qid_conflict = False
    dob_conflict = False

    for group in conflicts:

        providers.add(
            group["provider"]
        )

        external_ids.add(
            group["external_id"]
        )

        group_ids.append(
            group["group_id"]
        )

        if group["name_relation"] == (
            "different_normalized_label"
        ):
            name_conflict = True

        if group["gender_relation"] == (
            "different_gender"
        ):
            gender_conflict = True

        if group["qid_relation"] == (
            "different_qids"
        ):
            qid_conflict = True

        if group["dob_relation"] == (
            "mixed_dob_status"
        ):
            dob_conflict = True

    if conflict_count == 0:
        identity_status = "no_external_id_conflict"

    elif (
        qid_conflict
        or gender_conflict
        or dob_conflict
        or name_conflict
    ):
        identity_status = "identity_conflict"

    else:
        identity_status = "shared_external_id"

    player_records.append({
        "reep_id": reep_id,
        "label": player["label"],
        "status": player["status"],
        "gender": player["gender"],
        "conflict_group_count": conflict_count,
        "conflict_group_ids": ",".join(
            str(x)
            for x in sorted(group_ids)
        ),
        "conflict_providers": ",".join(
            sorted(providers)
        ),
        "conflict_external_ids": ",".join(
            sorted(external_ids)
        ),
        "name_conflict": name_conflict,
        "gender_conflict": gender_conflict,
        "qid_conflict": qid_conflict,
        "dob_status_conflict": dob_conflict,
        "identity_status": identity_status,
    })


# ======================================================================
# SUMMARY
# ======================================================================

players_in_conflicts = len(
    player_conflicts
)

identity_conflict_players = sum(
    1
    for row in player_records
    if row["identity_status"] == "identity_conflict"
)

shared_id_players = sum(
    1
    for row in player_records
    if row["identity_status"] == "shared_external_id"
)

players_without_conflicts = (
    len(players)
    - players_in_conflicts
)

print()
print("IDENTITY CONFLICT SUMMARY")
print("-" * 70)

print(
    f"Total REEP players:                 "
    f"{len(players):,}"
)

print(
    f"Provider+ID conflict groups:        "
    f"{len(conflict_groups):,}"
)

print(
    f"Players in conflict groups:         "
    f"{players_in_conflicts:,}"
)

print(
    f"Players without conflict groups:    "
    f"{players_without_conflicts:,}"
)

print()

print("NAME RELATIONSHIP")
print("-" * 70)

print(
    f"Same normalized label:              "
    f"{same_name_groups:,}"
)

print(
    f"Different normalized label:         "
    f"{different_name_groups:,}"
)

print()

print("GENDER RELATIONSHIP")
print("-" * 70)

print(
    f"Same/missing gender:                "
    f"{same_gender_groups:,}"
)

print(
    f"Different gender:                   "
    f"{different_gender_groups:,}"
)

print()

print("QID RELATIONSHIP")
print("-" * 70)

print(
    f"Shared QID:                         "
    f"{shared_qid_groups:,}"
)

print(
    f"Different QIDs:                     "
    f"{different_qid_groups:,}"
)

print(
    f"No QID:                             "
    f"{missing_qid_groups:,}"
)

print()

print("DOB STATUS RELATIONSHIP")
print("-" * 70)

print(
    f"Same DOB status:                    "
    f"{same_dob_groups:,}"
)

print(
    f"Mixed DOB status:                   "
    f"{mixed_dob_groups:,}"
)

print()

print("PLAYER IDENTITY PROFILES")
print("-" * 70)

print(
    f"Identity conflict:                  "
    f"{identity_conflict_players:,}"
)

print(
    f"Shared external ID only:            "
    f"{shared_id_players:,}"
)

print(
    f"No external-ID conflict:            "
    f"{players_without_conflicts:,}"
)

print()


# ======================================================================
# WRITE GROUP CSV
# ======================================================================

print("=" * 70)
print("WRITING CONFLICT-GROUP CSV")
print("=" * 70)

with open(
    GROUP_CSV,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "group_id",
        "provider",
        "external_id",
        "player_count",
        "reep_ids",
        "labels",
        "name_relation",
        "gender_relation",
        "qid_relation",
        "dob_relation",
        "properties",
    ])

    for group in group_records:

        writer.writerow([
            group["group_id"],
            group["provider"],
            group["external_id"],
            group["player_count"],
            "|".join(group["players"]),
            "|".join(group["labels"]),
            group["name_relation"],
            group["gender_relation"],
            group["qid_relation"],
            group["dob_relation"],
            "|".join(group["properties"]),
        ])

print(
    f"Group CSV written:\n  {GROUP_CSV}"
)
print()


# ======================================================================
# WRITE PLAYER CSV
# ======================================================================

print("=" * 70)
print("WRITING PLAYER-LEVEL CSV")
print("=" * 70)

with open(
    PLAYER_CSV,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "reep_id",
            "label",
            "status",
            "gender",
            "conflict_group_count",
            "conflict_group_ids",
            "conflict_providers",
            "conflict_external_ids",
            "name_conflict",
            "gender_conflict",
            "qid_conflict",
            "dob_status_conflict",
            "identity_status",
        ]
    )

    writer.writeheader()
    writer.writerows(player_records)

print(
    f"Player CSV written:\n  {PLAYER_CSV}"
)
print()


# ======================================================================
# JSON SUMMARY
# ======================================================================

print("=" * 70)
print("WRITING JSON SUMMARY")
print("=" * 70)

summary = {
    "audit": "REEP PLAYER EXTERNAL-ID IDENTITY AUDIT",
    "generated_at_utc": datetime.now(
        timezone.utc
    ).isoformat(),

    "source_database": DB_PATH,

    "read_only": True,

    "players": {
        "total": len(players),
        "players_in_conflict_groups": players_in_conflicts,
        "players_without_conflict_groups": players_without_conflicts,
    },

    "conflict_groups": {
        "provider_external_id_groups": len(conflict_groups),
        "same_normalized_label": same_name_groups,
        "different_normalized_label": different_name_groups,
        "same_or_missing_gender": same_gender_groups,
        "different_gender": different_gender_groups,
        "shared_qid": shared_qid_groups,
        "different_qids": different_qid_groups,
        "no_qid": missing_qid_groups,
        "same_dob_status": same_dob_groups,
        "mixed_dob_status": mixed_dob_groups,
        "exact_provider_property_groups": (
            exact_provider_property_groups
        ),
    },

    "player_profiles": {
        "identity_conflict": identity_conflict_players,
        "shared_external_id_only": shared_id_players,
        "no_external_id_conflict": players_without_conflicts,
    },

    "coverage": {
        "players_in_conflict_groups_percent": pct(
            players_in_conflicts,
            len(players)
        ),
        "identity_conflict_percent": pct(
            identity_conflict_players,
            len(players)
        ),
    },

    "output_files": {
        "player_csv": PLAYER_CSV,
        "group_csv": GROUP_CSV,
        "json": JSON_OUTPUT,
    }
}

with open(
    JSON_OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        summary,
        f,
        indent=2,
        ensure_ascii=False
    )

print(
    f"JSON written:\n  {JSON_OUTPUT}"
)
print()


# ======================================================================
# COMPLETE
# ======================================================================

print("=" * 70)
print("PLAYER EXTERNAL-ID IDENTITY AUDIT COMPLETE")
print("=" * 70)

print()
print(
    f"REEP players audited:               {len(players):,}"
)

print(
    f"External-ID conflict groups:        "
    f"{len(conflict_groups):,}"
)

print(
    f"Players in conflict groups:         "
    f"{players_in_conflicts:,}"
)

print(
    f"Identity conflict players:          "
    f"{identity_conflict_players:,}"
)

print(
    f"Shared external-ID-only players:    "
    f"{shared_id_players:,}"
)

print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")
print()
print("Output files:")
print(f"  {PLAYER_CSV}")
print(f"  {GROUP_CSV}")
print(f"  {JSON_OUTPUT}")
print()

con.close()