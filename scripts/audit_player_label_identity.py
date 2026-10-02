import csv
import json
import os
import re
import unicodedata
from collections import defaultdict, Counter
from datetime import datetime, timezone

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

PLAYER_CSV = os.path.join(
    OUTPUT_DIR,
    "reep-player-label-identity.csv"
)

GROUP_CSV = os.path.join(
    OUTPUT_DIR,
    "reep-label-identity-groups.csv"
)

JSON_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "reep-player-label-identity.json"
)


# ============================================================
# HELPERS
# ============================================================

def normalize_label(value):
    """
    Normalize a player label for identity comparison.

    This is intentionally conservative:
    - Unicode normalization
    - lowercase
    - remove accents
    - replace punctuation with spaces
    - collapse whitespace
    """
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        ch for ch in value
        if not unicodedata.combining(ch)
    )

    value = value.lower()

    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)

    value = re.sub(r"_+", " ", value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_value(value):
    if value is None:
        return ""

    value = str(value).strip()

    return value


def percentage(part, total):
    if total == 0:
        return 0.0

    return round((part / total) * 100, 2)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("REEP PLAYER LABEL IDENTITY AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()
print("Source database:")
print(DB_PATH)
print()


# ============================================================
# DATABASE CHECK
# ============================================================

if not os.path.isfile(DB_PATH):
    raise FileNotFoundError(
        f"Database not found:\n{DB_PATH}"
    )

os.makedirs(OUTPUT_DIR, exist_ok=True)

print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=DB_PATH,
    read_only=True
)

print("Connected successfully.")
print()


# ============================================================
# REQUIRED TABLE CHECK
# ============================================================

print("=" * 70)
print("CHECKING REQUIRED TABLES")
print("=" * 70)

tables = {
    row[0]
    for row in con.execute(
        "SHOW TABLES"
    ).fetchall()
}

if "players" not in tables:
    raise RuntimeError(
        "Required table 'players' was not found."
    )

print("  players              FOUND")
print()


# ============================================================
# PLAYER TABLE SCHEMA
# ============================================================

print("=" * 70)
print("LOADING PLAYER MASTER")
print("=" * 70)

schema_rows = con.execute(
    "DESCRIBE players"
).fetchall()

columns = [row[0] for row in schema_rows]

print("Players table columns:")
print("  " + ", ".join(columns))
print()

required_columns = [
    "reep_id",
    "label",
    "status",
    "gender",
]

missing = [
    col for col in required_columns
    if col not in columns
]

if missing:
    raise RuntimeError(
        "Missing required player columns: "
        + ", ".join(missing)
    )


# ============================================================
# LOAD PLAYERS
# ============================================================

players = con.execute(
    """
    SELECT
        reep_id,
        label,
        status,
        gender,
        country
    FROM players
    ORDER BY reep_id
    """
).fetchall()

total_players = len(players)

print(f"Total REEP players: {total_players:,}")
print()


# ============================================================
# BUILD PLAYER RECORDS
# ============================================================

player_records = []

for reep_id, label, status, gender, country in players:

    label_clean = clean_value(label)
    normalized = normalize_label(label)

    player_records.append(
        {
            "reep_id": clean_value(reep_id),
            "label": label_clean,
            "normalized_label": normalized,
            "status": clean_value(status),
            "gender": clean_value(gender),
            "country": clean_value(country),
        }
    )


# ============================================================
# LABEL COMPLETENESS
# ============================================================

print("=" * 70)
print("LABEL COMPLETENESS")
print("=" * 70)

players_with_label = sum(
    1
    for p in player_records
    if p["label"]
)

players_without_label = (
    total_players - players_with_label
)

distinct_labels = len(
    {
        p["label"]
        for p in player_records
        if p["label"]
    }
)

distinct_normalized_labels = len(
    {
        p["normalized_label"]
        for p in player_records
        if p["normalized_label"]
    }
)

print(
    f"Players with label:            "
    f"{players_with_label:,}"
)

print(
    f"Players without label:         "
    f"{players_without_label:,}"
)

print(
    f"Label coverage:                "
    f"{percentage(players_with_label, total_players):.2f}%"
)

print(
    f"Distinct labels:               "
    f"{distinct_labels:,}"
)

print(
    f"Distinct normalized labels:    "
    f"{distinct_normalized_labels:,}"
)

print()


# ============================================================
# BUILD EXACT LABEL GROUPS
# ============================================================

print("=" * 70)
print("BUILDING EXACT LABEL GROUPS")
print("=" * 70)

exact_groups = defaultdict(list)

for p in player_records:

    if p["label"]:
        exact_groups[p["label"]].append(
            p["reep_id"]
        )

exact_collision_groups = {
    label: ids
    for label, ids in exact_groups.items()
    if len(ids) > 1
}

players_in_exact_collisions = len(
    {
        reep_id
        for ids in exact_collision_groups.values()
        for reep_id in ids
    }
)

print(
    f"Exact label collision groups:       "
    f"{len(exact_collision_groups):,}"
)

print(
    f"Players in exact collisions:        "
    f"{players_in_exact_collisions:,}"
)

print()


# ============================================================
# BUILD NORMALIZED LABEL GROUPS
# ============================================================

print("=" * 70)
print("BUILDING NORMALIZED LABEL GROUPS")
print("=" * 70)

normalized_groups = defaultdict(list)

for p in player_records:

    if p["normalized_label"]:
        normalized_groups[
            p["normalized_label"]
        ].append(
            p["reep_id"]
        )

normalized_collision_groups = {
    label: ids
    for label, ids in normalized_groups.items()
    if len(ids) > 1
}

players_in_normalized_collisions = len(
    {
        reep_id
        for ids in normalized_collision_groups.values()
        for reep_id in ids
    }
)

print(
    f"Normalized label collision groups:  "
    f"{len(normalized_collision_groups):,}"
)

print(
    f"Players in normalized collisions:   "
    f"{players_in_normalized_collisions:,}"
)

print()


# ============================================================
# MAP PLAYERS
# ============================================================

player_by_id = {
    p["reep_id"]: p
    for p in player_records
}


# ============================================================
# ANALYZE COLLISION GROUPS
# ============================================================

print("=" * 70)
print("ANALYZING LABEL IDENTITY GROUPS")
print("=" * 70)

group_records = []

same_label_groups = 0
different_label_groups = 0

same_gender_groups = 0
different_gender_groups = 0
no_gender_groups = 0

group_sizes = Counter()

for normalized_label, ids in sorted(
    normalized_collision_groups.items()
):

    members = [
        player_by_id[reep_id]
        for reep_id in ids
        if reep_id in player_by_id
    ]

    if len(members) < 2:
        continue

    group_sizes[len(members)] += 1

    labels = sorted(
        {
            p["label"]
            for p in members
            if p["label"]
        }
    )

    genders = {
        p["gender"]
        for p in members
        if p["gender"]
    }

    qid_count = 0

    # QID evidence is checked separately below where possible.
    # This audit remains valid even when overlay tables are absent.

    if len(labels) == 1:
        same_label_groups += 1
        label_relationship = "same_label"
    else:
        different_label_groups += 1
        label_relationship = "different_label"

    if len(genders) == 0:
        no_gender_groups += 1
        gender_relationship = "no_gender"
    elif len(genders) == 1:
        same_gender_groups += 1
        gender_relationship = "same_gender"
    else:
        different_gender_groups += 1
        gender_relationship = "different_gender"

    group_records.append(
        {
            "normalized_label": normalized_label,
            "player_count": len(members),
            "reep_ids": "|".join(
                p["reep_id"]
                for p in members
            ),
            "labels": "|".join(labels),
            "genders": "|".join(
                sorted(genders)
            ),
            "label_relationship": label_relationship,
            "gender_relationship": gender_relationship,
        }
    )


# ============================================================
# OPTIONAL QID ANALYSIS
# ============================================================

print("Checking QID evidence...")

qid_by_player = defaultdict(set)

if "overlay_links" in tables:

    overlay_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE overlay_links"
        ).fetchall()
    ]

    if (
        "reep_id" in overlay_columns
        and "qid" in overlay_columns
    ):

        qid_rows = con.execute(
            """
            SELECT
                reep_id,
                qid
            FROM overlay_links
            WHERE reep_id IS NOT NULL
              AND qid IS NOT NULL
            """
        ).fetchall()

        player_ids = set(
            player_by_id.keys()
        )

        for reep_id, qid in qid_rows:

            reep_id = clean_value(reep_id)
            qid = clean_value(qid)

            if (
                reep_id in player_ids
                and qid
            ):
                qid_by_player[
                    reep_id
                ].add(qid)


# ============================================================
# ADD QID RELATIONSHIPS
# ============================================================

shared_qid_groups = 0
different_qid_groups = 0
no_qid_groups = 0

for group in group_records:

    ids = group["reep_ids"].split("|")

    qids = set()

    for reep_id in ids:
        qids.update(
            qid_by_player.get(
                reep_id,
                set()
            )
        )

    if not qids:
        no_qid_groups += 1
        relationship = "no_qid"

    elif len(qids) == 1:
        shared_qid_groups += 1
        relationship = "shared_qid"

    else:
        different_qid_groups += 1
        relationship = "different_qid"

    group["qid_relationship"] = relationship
    group["qids"] = "|".join(
        sorted(qids)
    )


# ============================================================
# PLAYER-LEVEL PROFILES
# ============================================================

print()
print("Building player-level label identity profiles...")

player_collision_map = defaultdict(list)

for group_index, group in enumerate(
    group_records,
    start=1
):

    for reep_id in group["reep_ids"].split("|"):

        player_collision_map[
            reep_id
        ].append(group_index)


player_output = []

for p in player_records:

    collision_groups = player_collision_map.get(
        p["reep_id"],
        []
    )

    if not p["label"]:

        profile = "no_label"

    elif not collision_groups:

        profile = "unique_label"

    else:

        profile = "label_collision"

    qids = qid_by_player.get(
        p["reep_id"],
        set()
    )

    player_output.append(
        {
            "reep_id": p["reep_id"],
            "label": p["label"],
            "normalized_label": p["normalized_label"],
            "status": p["status"],
            "gender": p["gender"],
            "country": p["country"],
            "label_profile": profile,
            "collision_group_count": len(
                collision_groups
            ),
            "qid_count": len(qids),
            "qids": "|".join(
                sorted(qids)
            ),
        }
    )


# ============================================================
# PROFILE SUMMARY
# ============================================================

profile_counts = Counter(
    row["label_profile"]
    for row in player_output
)

print()
print("=" * 70)
print("LABEL IDENTITY SUMMARY")
print("=" * 70)

print(
    f"Total REEP players:                  "
    f"{total_players:,}"
)

print(
    f"Players with labels:                 "
    f"{players_with_label:,}"
)

print(
    f"Players without labels:              "
    f"{players_without_label:,}"
)

print(
    f"Label coverage:                      "
    f"{percentage(players_with_label, total_players):.2f}%"
)

print()

print(
    f"Exact label collision groups:        "
    f"{len(exact_collision_groups):,}"
)

print(
    f"Players in exact collisions:         "
    f"{players_in_exact_collisions:,}"
)

print(
    f"Normalized collision groups:        "
    f"{len(normalized_collision_groups):,}"
)

print(
    f"Players in normalized collisions:   "
    f"{players_in_normalized_collisions:,}"
)

print()

print(
    f"Same-label collision groups:         "
    f"{same_label_groups:,}"
)

print(
    f"Different-label collision groups:    "
    f"{different_label_groups:,}"
)

print()

print(
    f"Same-gender collision groups:        "
    f"{same_gender_groups:,}"
)

print(
    f"Different-gender collision groups:   "
    f"{different_gender_groups:,}"
)

print(
    f"No-gender collision groups:          "
    f"{no_gender_groups:,}"
)

print()

print(
    f"Shared-QID collision groups:         "
    f"{shared_qid_groups:,}"
)

print(
    f"Different-QID collision groups:      "
    f"{different_qid_groups:,}"
)

print(
    f"No-QID collision groups:             "
    f"{no_qid_groups:,}"
)

print()

print(
    f"Unique-label players:                 "
    f"{profile_counts.get('unique_label', 0):,}"
)

print(
    f"Label-collision players:             "
    f"{profile_counts.get('label_collision', 0):,}"
)

print(
    f"No-label players:                    "
    f"{profile_counts.get('no_label', 0):,}"
)

print()


# ============================================================
# WRITE PLAYER CSV
# ============================================================

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
            "normalized_label",
            "status",
            "gender",
            "country",
            "label_profile",
            "collision_group_count",
            "qid_count",
            "qids",
        ]
    )

    writer.writeheader()

    writer.writerows(
        player_output
    )

print("Player CSV written:")
print(PLAYER_CSV)
print()


# ============================================================
# WRITE GROUP CSV
# ============================================================

print("=" * 70)
print("WRITING LABEL COLLISION GROUP CSV")
print("=" * 70)

with open(
    GROUP_CSV,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=[
            "normalized_label",
            "player_count",
            "reep_ids",
            "labels",
            "genders",
            "label_relationship",
            "gender_relationship",
            "qid_relationship",
            "qids",
        ]
    )

    writer.writeheader()

    writer.writerows(
        group_records
    )

print("Group CSV written:")
print(GROUP_CSV)
print()


# ============================================================
# JSON SUMMARY
# ============================================================

print("=" * 70)
print("WRITING JSON SUMMARY")
print("=" * 70)

summary = {
    "audit": "REEP PLAYER LABEL IDENTITY AUDIT",
    "generated_at_utc": datetime.now(
        timezone.utc
    ).isoformat(),

    "database": DB_PATH,

    "read_only": True,

    "total_players": total_players,

    "label_completeness": {
        "players_with_label": players_with_label,
        "players_without_label": players_without_label,
        "coverage_percent": percentage(
            players_with_label,
            total_players
        ),
        "distinct_labels": distinct_labels,
        "distinct_normalized_labels":
            distinct_normalized_labels,
    },

    "exact_label_collisions": {
        "groups": len(
            exact_collision_groups
        ),
        "players": players_in_exact_collisions,
    },

    "normalized_label_collisions": {
        "groups": len(
            normalized_collision_groups
        ),
        "players":
            players_in_normalized_collisions,
    },

    "collision_relationships": {
        "same_label_groups":
            same_label_groups,
        "different_label_groups":
            different_label_groups,
        "same_gender_groups":
            same_gender_groups,
        "different_gender_groups":
            different_gender_groups,
        "no_gender_groups":
            no_gender_groups,
        "shared_qid_groups":
            shared_qid_groups,
        "different_qid_groups":
            different_qid_groups,
        "no_qid_groups":
            no_qid_groups,
    },

    "player_profiles": dict(
        profile_counts
    ),

    "collision_group_size_distribution": {
        str(size): count
        for size, count in sorted(
            group_sizes.items()
        )
    },

    "outputs": {
        "player_csv": PLAYER_CSV,
        "group_csv": GROUP_CSV,
        "json": JSON_OUTPUT,
    },

    "source_database_modified": False,
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

print("JSON written:")
print(JSON_OUTPUT)
print()


# ============================================================
# FINISH
# ============================================================

con.close()

print("=" * 70)
print("PLAYER LABEL IDENTITY AUDIT COMPLETE")
print("=" * 70)
print()
print(
    f"REEP players audited:               "
    f"{total_players:,}"
)

print(
    f"Players with labels:                "
    f"{players_with_label:,}"
)

print(
    f"Normalized label collision groups:  "
    f"{len(normalized_collision_groups):,}"
)

print(
    f"Players in label collisions:        "
    f"{players_in_normalized_collisions:,}"
)

print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")
print()
print("Output files:")
print(PLAYER_CSV)
print(GROUP_CSV)
print(JSON_OUTPUT)
print()
print("=" * 70)