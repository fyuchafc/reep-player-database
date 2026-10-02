import duckdb
import csv
import json
import os
import re
from collections import defaultdict, Counter
from datetime import datetime, timezone

# ==============================================================
# CONFIGURATION
# ==============================================================

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
    "reep-player-gender-identity.csv"
)

JSON_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-gender-identity.json"
)


# ==============================================================
# HELPERS
# ==============================================================

def header(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def normalize_label(value):
    if value is None:
        return ""

    value = str(value).strip().lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return re.sub(r"\s+", " ", value).strip()


def clean_gender(value):
    if value is None:
        return None

    value = str(value).strip().lower()

    if not value:
        return None

    return value


def safe_int(value):
    try:
        return int(value)
    except Exception:
        return 0


# ==============================================================
# START
# ==============================================================

header("REEP PLAYER GENDER IDENTITY AUDIT")

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

print()
print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=DB_PATH,
    read_only=True
)

print("Connected successfully.")


# ==============================================================
# REQUIRED TABLES
# ==============================================================

header("CHECKING REQUIRED TABLES")

tables = {
    row[0]
    for row in con.execute(
        "SHOW TABLES"
    ).fetchall()
}

required_tables = [
    "players",
    "entities",
    "overlay_links",
    "overlay_xids",
    "aliases",
    "overlay_aliases",
]

for table in required_tables:
    if table in tables:
        print(f"  {table:<20} FOUND")
    else:
        print(f"  {table:<20} MISSING")

if "players" not in tables:
    raise RuntimeError(
        "Required table 'players' was not found."
    )


# ==============================================================
# PLAYER TABLE
# ==============================================================

header("LOADING PLAYER MASTER")

player_columns = [
    row[0]
    for row in con.execute(
        "DESCRIBE players"
    ).fetchall()
]

print("Players table columns:")
print(", ".join(player_columns))

required_player_columns = [
    "reep_id",
    "label",
    "status",
    "gender",
]

missing_player_columns = [
    c for c in required_player_columns
    if c not in player_columns
]

if missing_player_columns:
    raise RuntimeError(
        "Missing required player columns: "
        + ", ".join(missing_player_columns)
    )

players = con.execute(
    """
    SELECT
        reep_id,
        label,
        status,
        gender
    FROM players
    ORDER BY reep_id
    """
).fetchall()

print()
print(f"Total REEP players: {len(players):,}")


player_map = {}

for reep_id, label, status, gender in players:
    player_map[reep_id] = {
        "reep_id": reep_id,
        "label": label,
        "status": status,
        "gender": clean_gender(gender),
        "normalized_label": normalize_label(label),
    }


# ==============================================================
# MASTER GENDER SUMMARY
# ==============================================================

header("MASTER GENDER COMPLETENESS")

gender_counts = Counter()

for p in player_map.values():
    gender = p["gender"]

    if gender is None:
        gender_counts["NULL/BLANK"] += 1
    else:
        gender_counts[gender] += 1

gender_present = len(players) - gender_counts["NULL/BLANK"]
gender_missing = gender_counts["NULL/BLANK"]

coverage = (
    (gender_present / len(players)) * 100
    if players else 0
)

print(
    f"Gender present:       {gender_present:,}"
)

print(
    f"Gender missing:       {gender_missing:,}"
)

print(
    f"Gender coverage:      {coverage:.2f}%"
)

print()
print("Gender distribution:")

for gender, count in gender_counts.most_common():
    print(
        f"  {gender:<20} {count:,}"
    )


# ==============================================================
# ENTITY GENDER EVIDENCE
# ==============================================================

entity_gender = {}
entity_gender_different = 0
entity_gender_matching = 0

if "entities" in tables:

    header("ENTITY GENDER EVIDENCE")

    entity_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE entities"
        ).fetchall()
    ]

    print("Entities table columns:")
    print(", ".join(entity_columns))

    if "reep_id" in entity_columns and "gender" in entity_columns:

        entity_rows = con.execute(
            """
            SELECT
                reep_id,
                gender
            FROM entities
            WHERE reep_id IS NOT NULL
            """
        ).fetchall()

        for reep_id, gender in entity_rows:

            if reep_id not in player_map:
                continue

            gender = clean_gender(gender)

            if gender is None:
                continue

            entity_gender.setdefault(
                reep_id,
                set()
            ).add(gender)

        for reep_id, values in entity_gender.items():

            if len(values) != 1:
                continue

            entity_value = next(iter(values))
            master_value = player_map[reep_id]["gender"]

            if master_value is None:
                continue

            if entity_value == master_value:
                entity_gender_matching += 1
            else:
                entity_gender_different += 1

        print()
        print(
            f"Players with entity gender: "
            f"{len(entity_gender):,}"
        )

        print(
            f"Master/entity gender matching: "
            f"{entity_gender_matching:,}"
        )

        print(
            f"Master/entity gender different: "
            f"{entity_gender_different:,}"
        )

    else:
        print(
            "Required entity gender columns were not available."
        )


# ==============================================================
# QID GENDER PATHWAY
# ==============================================================

header("QID / WIKIDATA GENDER PATHWAY")

qid_gender_players = set()

if "overlay_links" in tables:

    overlay_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE overlay_links"
        ).fetchall()
    ]

    print("overlay_links columns:")
    print(", ".join(overlay_columns))

    if "reep_id" in overlay_columns:

        qid_rows = con.execute(
            """
            SELECT DISTINCT reep_id
            FROM overlay_links
            WHERE reep_id IS NOT NULL
            """
        ).fetchall()

        for (reep_id,) in qid_rows:

            if reep_id in player_map:
                qid_gender_players.add(
                    reep_id
                )

print(
    f"Players with QID pathway: "
    f"{len(qid_gender_players):,}"
)


# ==============================================================
# EXTERNAL-ID GENDER PATHWAY
# ==============================================================

header("EXTERNAL-ID GENDER PATHWAY")

xid_players = set()
provider_players = defaultdict(set)

if "overlay_xids" in tables:

    xid_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE overlay_xids"
        ).fetchall()
    ]

    print("overlay_xids columns:")
    print(", ".join(xid_columns))

    if "reep_id" in xid_columns:

        if "provider" in xid_columns:

            xid_rows = con.execute(
                """
                SELECT
                    reep_id,
                    provider
                FROM overlay_xids
                WHERE reep_id IS NOT NULL
                """
            ).fetchall()

            for reep_id, provider in xid_rows:

                if reep_id not in player_map:
                    continue

                xid_players.add(
                    reep_id
                )

                if provider:
                    provider_players[
                        str(provider)
                    ].add(reep_id)

        else:

            xid_rows = con.execute(
                """
                SELECT DISTINCT reep_id
                FROM overlay_xids
                WHERE reep_id IS NOT NULL
                """
            ).fetchall()

            for (reep_id,) in xid_rows:

                if reep_id in player_map:
                    xid_players.add(
                        reep_id
                    )

print(
    f"Players with external-ID pathway: "
    f"{len(xid_players):,}"
)

print()
print("Top external-ID providers by player coverage:")

provider_summary = sorted(
    provider_players.items(),
    key=lambda x: len(x[1]),
    reverse=True
)

for provider, ids in provider_summary[:25]:

    print(
        f"  {provider:<30} "
        f"{len(ids):,}"
    )


# ==============================================================
# ALIAS PATHWAY
# ==============================================================

header("ALIAS IDENTITY PATHWAY")

alias_players = set()

if "aliases" in tables:

    alias_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE aliases"
        ).fetchall()
    ]

    print("aliases columns:")
    print(", ".join(alias_columns))

    if "reep_id" in alias_columns:

        rows = con.execute(
            """
            SELECT DISTINCT reep_id
            FROM aliases
            WHERE reep_id IS NOT NULL
            """
        ).fetchall()

        for (reep_id,) in rows:

            if reep_id in player_map:
                alias_players.add(
                    reep_id
                )

print(
    f"Players with aliases: "
    f"{len(alias_players):,}"
)


# ==============================================================
# OVERLAY ALIAS PATHWAY
# ==============================================================

header("OVERLAY ALIAS IDENTITY PATHWAY")

overlay_alias_players = set()

if "overlay_aliases" in tables:

    overlay_alias_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE overlay_aliases"
        ).fetchall()
    ]

    print("overlay_aliases columns:")
    print(", ".join(overlay_alias_columns))

    if "reep_id" in overlay_alias_columns:

        rows = con.execute(
            """
            SELECT DISTINCT reep_id
            FROM overlay_aliases
            WHERE reep_id IS NOT NULL
            """
        ).fetchall()

        for (reep_id,) in rows:

            if reep_id in player_map:
                overlay_alias_players.add(
                    reep_id
                )

print(
    f"Players with overlay aliases: "
    f"{len(overlay_alias_players):,}"
)


# ==============================================================
# LABEL COLLISION ANALYSIS
# ==============================================================

header("LABEL / GENDER RELATIONSHIPS")

label_groups = defaultdict(list)

for p in player_map.values():

    normalized = p["normalized_label"]

    if normalized:
        label_groups[
            normalized
        ].append(
            p["reep_id"]
        )

collision_groups = {
    label: ids
    for label, ids in label_groups.items()
    if len(ids) > 1
}

print(
    f"Normalized label collision groups: "
    f"{len(collision_groups):,}"
)

collision_players = set()

same_gender_groups = 0
different_gender_groups = 0
no_gender_groups = 0
mixed_gender_groups = 0

for label, ids in collision_groups.items():

    collision_players.update(ids)

    genders = {
        player_map[i]["gender"]
        for i in ids
        if player_map[i]["gender"] is not None
    }

    if not genders:
        no_gender_groups += 1

    elif len(genders) == 1:
        same_gender_groups += 1

    else:
        different_gender_groups += 1

        if len(genders) > 1:
            mixed_gender_groups += 1

print(
    f"Same-gender collision groups: "
    f"{same_gender_groups:,}"
)

print(
    f"Different-gender collision groups: "
    f"{different_gender_groups:,}"
)

print(
    f"No-gender collision groups: "
    f"{no_gender_groups:,}"
)


# ==============================================================
# IDENTITY PATHWAY ANALYSIS
# ==============================================================

header("GENDER IDENTITY PATHWAY CLASSIFICATION")

profiles = Counter()

for reep_id, p in player_map.items():

    has_gender = (
        p["gender"] is not None
    )

    has_qid = (
        reep_id in qid_gender_players
    )

    has_xid = (
        reep_id in xid_players
    )

    has_alias = (
        reep_id in alias_players
    )

    has_overlay_alias = (
        reep_id in overlay_alias_players
    )

    if has_gender and has_qid and has_xid:
        profile = "gender_qid_xid"

    elif has_gender and has_qid:
        profile = "gender_qid"

    elif has_gender and has_xid:
        profile = "gender_xid"

    elif has_gender and has_alias:
        profile = "gender_alias"

    elif has_gender:
        profile = "gender_only"

    elif has_qid and has_xid:
        profile = "qid_xid_no_gender"

    elif has_qid:
        profile = "qid_no_gender"

    elif has_xid:
        profile = "xid_no_gender"

    elif has_alias or has_overlay_alias:
        profile = "alias_no_gender"

    else:
        profile = "no_gender_evidence"

    profiles[profile] += 1


for profile, count in profiles.most_common():

    percentage = (
        count / len(player_map) * 100
        if player_map else 0
    )

    print(
        f"  {profile:<25} "
        f"{count:>10,} "
        f"({percentage:6.2f}%)"
    )


# ==============================================================
# MISSING-GENDER INDIRECT EVIDENCE
# ==============================================================

header("MISSING-GENDER INDIRECT EVIDENCE")

missing_gender_with_qid = 0
missing_gender_with_xid = 0
missing_gender_with_alias = 0
missing_gender_with_any_path = 0

for reep_id, p in player_map.items():

    if p["gender"] is not None:
        continue

    has_qid = reep_id in qid_gender_players
    has_xid = reep_id in xid_players
    has_alias = (
        reep_id in alias_players
        or reep_id in overlay_alias_players
    )

    if has_qid:
        missing_gender_with_qid += 1

    if has_xid:
        missing_gender_with_xid += 1

    if has_alias:
        missing_gender_with_alias += 1

    if has_qid or has_xid or has_alias:
        missing_gender_with_any_path += 1

print(
    f"Missing gender + QID:       "
    f"{missing_gender_with_qid:,}"
)

print(
    f"Missing gender + external ID: "
    f"{missing_gender_with_xid:,}"
)

print(
    f"Missing gender + alias:      "
    f"{missing_gender_with_alias:,}"
)

print(
    f"Missing gender + any pathway: "
    f"{missing_gender_with_any_path:,}"
)


# ==============================================================
# MASTER VS ENTITY CONFLICTS
# ==============================================================

header("MASTER / ENTITY GENDER CONFLICTS")

gender_conflict_players = []

for reep_id, values in entity_gender.items():

    if len(values) != 1:
        continue

    entity_value = next(iter(values))
    master_value = player_map[reep_id]["gender"]

    if (
        master_value is not None
        and entity_value != master_value
    ):
        gender_conflict_players.append(
            reep_id
        )

print(
    f"Gender conflicts between master/entity: "
    f"{len(gender_conflict_players):,}"
)


# ==============================================================
# BUILD PLAYER-LEVEL REPORT
# ==============================================================

header("BUILDING PLAYER-LEVEL GENDER IDENTITY REPORT")

report_rows = []

for reep_id, p in player_map.items():

    master_gender = p["gender"]

    entity_values = entity_gender.get(
        reep_id,
        set()
    )

    entity_gender_value = None

    if len(entity_values) == 1:
        entity_gender_value = next(
            iter(entity_values)
        )

    has_qid = (
        reep_id in qid_gender_players
    )

    has_xid = (
        reep_id in xid_players
    )

    has_alias = (
        reep_id in alias_players
    )

    has_overlay_alias = (
        reep_id in overlay_alias_players
    )

    label_collision = (
        reep_id in collision_players
    )

    entity_conflict = (
        master_gender is not None
        and entity_gender_value is not None
        and master_gender != entity_gender_value
    )

    if master_gender is None:

        if has_qid and has_xid:
            classification = "missing_gender_qid_xid"

        elif has_qid:
            classification = "missing_gender_qid"

        elif has_xid:
            classification = "missing_gender_xid"

        elif has_alias or has_overlay_alias:
            classification = "missing_gender_alias"

        else:
            classification = "missing_gender_no_path"

    else:

        if entity_conflict:
            classification = "gender_entity_conflict"

        elif label_collision:
            classification = "gender_with_label_collision"

        elif has_qid and has_xid:
            classification = "gender_qid_xid"

        elif has_qid:
            classification = "gender_qid"

        elif has_xid:
            classification = "gender_xid"

        else:
            classification = "gender_no_indirect_path"

    report_rows.append({
        "reep_id": reep_id,
        "label": p["label"],
        "normalized_label": p["normalized_label"],
        "status": p["status"],
        "master_gender": master_gender,
        "entity_gender": entity_gender_value,
        "entity_gender_values": "|".join(
            sorted(entity_values)
        ),
        "has_qid": has_qid,
        "has_external_id": has_xid,
        "has_alias": has_alias,
        "has_overlay_alias": has_overlay_alias,
        "label_collision": label_collision,
        "entity_gender_conflict": entity_conflict,
        "classification": classification,
    })


# ==============================================================
# WRITE CSV
# ==============================================================

header("WRITING PLAYER-LEVEL CSV")

csv_fields = [
    "reep_id",
    "label",
    "normalized_label",
    "status",
    "master_gender",
    "entity_gender",
    "entity_gender_values",
    "has_qid",
    "has_external_id",
    "has_alias",
    "has_overlay_alias",
    "label_collision",
    "entity_gender_conflict",
    "classification",
]

with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=csv_fields
    )

    writer.writeheader()

    for row in report_rows:
        writer.writerow(row)

print(
    f"CSV written:\n{CSV_PATH}"
)


# ==============================================================
# JSON SUMMARY
# ==============================================================

header("WRITING JSON SUMMARY")

summary = {
    "audit": "REEP PLAYER GENDER IDENTITY AUDIT",

    "generated_at_utc": (
        datetime.now(timezone.utc)
        .isoformat()
    ),

    "database": DB_PATH,

    "read_only": True,

    "total_players": len(player_map),

    "gender": {
        "present": gender_present,
        "missing": gender_missing,
        "coverage_percent": round(
            coverage,
            2
        ),
        "distribution": dict(
            gender_counts
        ),
    },

    "entity_gender": {
        "players_with_entity_gender": len(
            entity_gender
        ),
        "matching_master": (
            entity_gender_matching
        ),
        "different_from_master": (
            entity_gender_different
        ),
        "conflict_players": len(
            gender_conflict_players
        ),
    },

    "identity_pathways": {
        "qid_players": len(
            qid_gender_players
        ),
        "external_id_players": len(
            xid_players
        ),
        "alias_players": len(
            alias_players
        ),
        "overlay_alias_players": len(
            overlay_alias_players
        ),
    },

    "label_collisions": {
        "collision_groups": len(
            collision_groups
        ),
        "collision_players": len(
            collision_players
        ),
        "same_gender_groups": (
            same_gender_groups
        ),
        "different_gender_groups": (
            different_gender_groups
        ),
        "no_gender_groups": (
            no_gender_groups
        ),
    },

    "missing_gender_indirect_evidence": {
        "qid": missing_gender_with_qid,
        "external_id": missing_gender_with_xid,
        "alias": missing_gender_with_alias,
        "any_path": missing_gender_with_any_path,
    },

    "profiles": dict(
        profiles
    ),

    "outputs": {
        "csv": CSV_PATH,
        "json": JSON_PATH,
    },

    "source_database_modified": False,
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

print(
    f"JSON written:\n{JSON_PATH}"
)


# ==============================================================
# FINAL SUMMARY
# ==============================================================

header("PLAYER GENDER IDENTITY AUDIT COMPLETE")

print(
    f"REEP players audited:              "
    f"{len(player_map):,}"
)

print(
    f"Gender present:                     "
    f"{gender_present:,}"
)

print(
    f"Gender missing:                     "
    f"{gender_missing:,}"
)

print(
    f"Gender coverage:                    "
    f"{coverage:.2f}%"
)

print(
    f"Players with QID pathway:           "
    f"{len(qid_gender_players):,}"
)

print(
    f"Players with external-ID pathway:   "
    f"{len(xid_players):,}"
)

print(
    f"Players with aliases:               "
    f"{len(alias_players):,}"
)

print(
    f"Label collision players:            "
    f"{len(collision_players):,}"
)

print(
    f"Master/entity gender conflicts:      "
    f"{len(gender_conflict_players):,}"
)

print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")

print()
print("Output files:")
print(CSV_PATH)
print(JSON_PATH)

con.close()