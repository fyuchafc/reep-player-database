import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb


# ============================================================
# CONFIGURATION
# ============================================================

DB_PATH = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\reep-player-database-main\output"
)

PLAYER_CSV = OUTPUT_DIR / "reep-player-alias-identity.csv"
GROUP_CSV = OUTPUT_DIR / "reep-alias-identity-groups.csv"
JSON_OUTPUT = OUTPUT_DIR / "reep-player-alias-identity.json"


# ============================================================
# HELPERS
# ============================================================

def normalize_text(value):
    """
    Normalize names/aliases for identity comparison.

    - Unicode normalization
    - lowercase
    - removes accents
    - converts punctuation to spaces
    - collapses whitespace
    """
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    value = unicodedata.normalize("NFKD", value)

    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()

    value = re.sub(r"[^a-z0-9]+", " ", value)

    value = re.sub(r"\s+", " ", value).strip()

    return value


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def pct(value, total):
    if not total:
        return 0.0
    return round((value / total) * 100, 2)


def print_header(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# START
# ============================================================

print_header("REEP PLAYER ALIAS IDENTITY AUDIT")

print()
print("READ-ONLY — source database will NOT be modified.")
print()
print("Source database:")
print(DB_PATH)

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"\nDatabase not found:\n{DB_PATH}"
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print()
print("Opening REEP database READ-ONLY...")

con = duckdb.connect(
    database=str(DB_PATH),
    read_only=True
)

print("Connected successfully.")


# ============================================================
# CHECK REQUIRED TABLES
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
    "aliases",
    "overlay_aliases",
    "overlay_links",
    "overlay_xids",
]

for table in required_tables:
    if table in tables:
        print(f"  {table:<18} FOUND")
    else:
        print(f"  {table:<18} MISSING")

if "players" not in tables:
    raise RuntimeError("Required table 'players' was not found.")

if "aliases" not in tables:
    raise RuntimeError("Required table 'aliases' was not found.")


# ============================================================
# PLAYER MASTER
# ============================================================

print_header("LOADING PLAYER MASTER")

player_columns = [
    row[0]
    for row in con.execute(
        "DESCRIBE players"
    ).fetchall()
]

print("Players table columns:")
print("  " + ", ".join(player_columns))

required_player_columns = {
    "reep_id",
    "label",
    "status",
    "gender",
}

missing = required_player_columns - set(player_columns)

if missing:
    raise RuntimeError(
        "Missing required player columns: "
        + ", ".join(sorted(missing))
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

player_map = {}

for reep_id, label, status, gender in players:
    player_map[str(reep_id)] = {
        "reep_id": str(reep_id),
        "label": safe_text(label),
        "status": safe_text(status),
        "gender": safe_text(gender),
    }

total_players = len(player_map)

print()
print(f"Total REEP players: {total_players:,}")


# ============================================================
# LOAD ALIASES
# ============================================================

print_header("LOADING PLAYER ALIASES")

alias_columns = [
    row[0]
    for row in con.execute(
        "DESCRIBE aliases"
    ).fetchall()
]

print("aliases columns:")
print("  " + ", ".join(alias_columns))

if "reep_id" not in alias_columns:
    raise RuntimeError(
        "aliases table does not contain reep_id."
    )

if "alias" not in alias_columns:
    raise RuntimeError(
        "aliases table does not contain alias."
    )

has_kind = "kind" in alias_columns
has_rank = "rank" in alias_columns
has_language = "language" in alias_columns

alias_select = [
    "reep_id",
    "alias",
]

if has_kind:
    alias_select.append("kind")

if has_rank:
    alias_select.append('"rank"')

if has_language:
    alias_select.append("language")

alias_rows = con.execute(
    f"""
    SELECT
        {", ".join(alias_select)}
    FROM aliases
    WHERE reep_id IS NOT NULL
      AND alias IS NOT NULL
      AND TRIM(CAST(alias AS VARCHAR)) <> ''
    """
).fetchall()

print()
print(f"Total usable alias rows: {len(alias_rows):,}")


# ============================================================
# BUILD ALIAS RECORDS
# ============================================================

print()
print("Building alias records...")

player_aliases = defaultdict(list)

alias_player_membership = defaultdict(set)

alias_exact_groups = defaultdict(set)

alias_normalized_groups = defaultdict(set)

player_alias_count = Counter()

player_alias_values = defaultdict(set)

player_alias_kinds = defaultdict(set)

player_alias_languages = defaultdict(set)


for row in alias_rows:

    reep_id = str(row[0])

    if reep_id not in player_map:
        continue

    alias_value = safe_text(row[1])

    if not alias_value:
        continue

    normalized = normalize_text(alias_value)

    if not normalized:
        continue

    kind = ""
    rank = ""
    language = ""

    index = 2

    if has_kind:
        kind = safe_text(row[index])
        index += 1

    if has_rank:
        rank = safe_text(row[index])
        index += 1

    if has_language:
        language = safe_text(row[index])

    record = {
        "reep_id": reep_id,
        "alias": alias_value,
        "normalized_alias": normalized,
        "kind": kind,
        "rank": rank,
        "language": language,
    }

    player_aliases[reep_id].append(record)

    alias_player_membership[alias_value].add(reep_id)

    alias_exact_groups[alias_value].add(reep_id)

    alias_normalized_groups[normalized].add(reep_id)

    player_alias_count[reep_id] += 1

    player_alias_values[reep_id].add(alias_value)

    if kind:
        player_alias_kinds[reep_id].add(kind)

    if language:
        player_alias_languages[reep_id].add(language)


players_with_aliases = len(player_aliases)

players_without_aliases = (
    total_players - players_with_aliases
)

print()
print(
    f"Players with aliases:    {players_with_aliases:,}"
)

print(
    f"Players without aliases: {players_without_aliases:,}"
)

print(
    f"Alias coverage:          "
    f"{pct(players_with_aliases, total_players):.2f}%"
)


# ============================================================
# EXACT ALIAS COLLISIONS
# ============================================================

print_header("EXACT ALIAS COLLISIONS")

exact_collision_groups = {
    alias: players_set
    for alias, players_set
    in alias_exact_groups.items()
    if len(players_set) > 1
}

exact_collision_players = set()

for players_set in exact_collision_groups.values():
    exact_collision_players.update(players_set)

print(
    f"Exact alias collision groups: "
    f"{len(exact_collision_groups):,}"
)

print(
    f"Players in exact alias collisions: "
    f"{len(exact_collision_players):,}"
)


# ============================================================
# NORMALIZED ALIAS COLLISIONS
# ============================================================

print_header("NORMALIZED ALIAS COLLISIONS")

normalized_collision_groups = {
    normalized: players_set
    for normalized, players_set
    in alias_normalized_groups.items()
    if len(players_set) > 1
}

normalized_collision_players = set()

for players_set in normalized_collision_groups.values():
    normalized_collision_players.update(players_set)

print(
    f"Normalized collision groups: "
    f"{len(normalized_collision_groups):,}"
)

print(
    f"Players in normalized collision groups: "
    f"{len(normalized_collision_players):,}"
)


# ============================================================
# ANALYZE COLLISION GROUPS
# ============================================================

print_header("ANALYZING ALIAS IDENTITY GROUPS")

group_records = []

same_label_groups = 0
different_label_groups = 0

same_gender_groups = 0
different_gender_groups = 0
missing_gender_groups = 0

shared_qid_groups = 0
different_qid_groups = 0
no_qid_groups = 0

shared_external_id_groups = 0
different_external_id_groups = 0
no_external_id_groups = 0

same_status_groups = 0
mixed_status_groups = 0


# ============================================================
# QID EVIDENCE
# ============================================================

player_qids = defaultdict(set)

if "overlay_links" in tables:

    qid_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE overlay_links"
        ).fetchall()
    ]

    if "reep_id" in qid_columns and "qid" in qid_columns:

        qid_rows = con.execute(
            """
            SELECT
                reep_id,
                qid
            FROM overlay_links
            WHERE reep_id IS NOT NULL
              AND qid IS NOT NULL
              AND TRIM(CAST(qid AS VARCHAR)) <> ''
            """
        ).fetchall()

        for reep_id, qid in qid_rows:

            rid = str(reep_id)

            if rid in player_map:
                player_qids[rid].add(
                    str(qid).strip()
                )


# ============================================================
# EXTERNAL ID EVIDENCE
# ============================================================

player_xids = defaultdict(set)

if "overlay_xids" in tables:

    xid_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE overlay_xids"
        ).fetchall()
    ]

    xid_required = {
        "reep_id",
        "provider",
        "external_id",
    }

    if xid_required.issubset(set(xid_columns)):

        xid_rows = con.execute(
            """
            SELECT
                reep_id,
                provider,
                external_id
            FROM overlay_xids
            WHERE reep_id IS NOT NULL
              AND provider IS NOT NULL
              AND external_id IS NOT NULL
              AND TRIM(CAST(external_id AS VARCHAR)) <> ''
            """
        ).fetchall()

        for reep_id, provider, external_id in xid_rows:

            rid = str(reep_id)

            if rid not in player_map:
                continue

            key = (
                safe_text(provider),
                safe_text(external_id),
            )

            player_xids[rid].add(key)


# ============================================================
# PROCESS NORMALIZED COLLISION GROUPS
# ============================================================

sorted_groups = sorted(
    normalized_collision_groups.items(),
    key=lambda item: (
        -len(item[1]),
        item[0],
    )
)

for group_number, (normalized_alias, member_ids) in enumerate(
    sorted_groups,
    start=1
):

    member_ids = sorted(member_ids)

    labels = {
        player_map[rid]["label"]
        for rid in member_ids
    }

    genders = {
        player_map[rid]["gender"]
        for rid in member_ids
        if player_map[rid]["gender"]
    }

    statuses = {
        player_map[rid]["status"]
        for rid in member_ids
        if player_map[rid]["status"]
    }

    qids = set()

    for rid in member_ids:
        qids.update(player_qids.get(rid, set()))

    xids = set()

    for rid in member_ids:
        xids.update(player_xids.get(rid, set()))

    if len(labels) == 1:
        same_label_groups += 1
        label_relationship = "same_label"
    else:
        different_label_groups += 1
        label_relationship = "different_label"

    if len(genders) == 0:
        missing_gender_groups += 1
        gender_relationship = "no_gender"
    elif len(genders) == 1:
        same_gender_groups += 1
        gender_relationship = "same_gender"
    else:
        different_gender_groups += 1
        gender_relationship = "different_gender"

    if len(qids) == 0:
        no_qid_groups += 1
        qid_relationship = "no_qid"
    elif len(qids) == 1:
        shared_qid_groups += 1
        qid_relationship = "shared_qid"
    else:
        different_qid_groups += 1
        qid_relationship = "different_qids"

    if len(xids) == 0:
        no_external_id_groups += 1
        xid_relationship = "no_shared_external_id"
    elif len(xids) < sum(
        len(player_xids.get(rid, set()))
        for rid in member_ids
    ):
        shared_external_id_groups += 1
        xid_relationship = "shared_external_id"
    else:
        different_external_id_groups += 1
        xid_relationship = "different_external_ids"

    if len(statuses) <= 1:
        same_status_groups += 1
        status_relationship = "same_status"
    else:
        mixed_status_groups += 1
        status_relationship = "mixed_status"

    group_records.append({
        "group_id": group_number,
        "normalized_alias": normalized_alias,
        "member_count": len(member_ids),
        "reep_ids": "|".join(member_ids),
        "labels": "|".join(
            sorted(labels)
        ),
        "label_relationship": label_relationship,
        "genders": "|".join(
            sorted(genders)
        ),
        "gender_relationship": gender_relationship,
        "qids": "|".join(
            sorted(qids)
        ),
        "qid_relationship": qid_relationship,
        "external_ids": "|".join(
            f"{provider}:{external_id}"
            for provider, external_id in sorted(xids)
        ),
        "external_id_relationship": xid_relationship,
        "statuses": "|".join(
            sorted(statuses)
        ),
        "status_relationship": status_relationship,
    })


# ============================================================
# PLAYER-LEVEL IDENTITY PROFILES
# ============================================================

print()
print("Building player-level alias identity profiles...")

player_group_memberships = defaultdict(list)

for record in group_records:

    for rid in record["reep_ids"].split("|"):

        if rid:
            player_group_memberships[rid].append(
                record["group_id"]
            )


player_identity_profiles = {}

for rid, player in player_map.items():

    alias_count = player_alias_count.get(rid, 0)

    exact_groups = []

    for alias in player_alias_values.get(rid, set()):

        members = alias_exact_groups.get(alias, set())

        if len(members) > 1:
            exact_groups.append(alias)

    normalized_groups = player_group_memberships.get(
        rid,
        []
    )

    if normalized_groups:
        profile = "alias_identity_conflict"

    elif alias_count > 0:
        profile = "alias_only_no_collision"

    else:
        profile = "no_alias"

    player_identity_profiles[rid] = {
        "profile": profile,
        "alias_count": alias_count,
        "exact_collision_count": len(exact_groups),
        "normalized_collision_count": len(normalized_groups),
        "exact_collision_aliases": exact_groups,
        "normalized_collision_groups": normalized_groups,
    }


profile_counts = Counter(
    data["profile"]
    for data in player_identity_profiles.values()
)


# ============================================================
# PROVIDER-NAME ALIASES
# ============================================================

print()
print("Analyzing alias kinds...")

provider_name_players = set()
short_alias_players = set()

for rid, records in player_aliases.items():

    for record in records:

        kind = record["kind"].lower()

        alias_value = record["alias"]

        if "provider" in kind:
            provider_name_players.add(rid)

        if len(alias_value.split()) <= 2:
            short_alias_players.add(rid)


# ============================================================
# SUMMARY
# ============================================================

print_header("ALIAS IDENTITY SUMMARY")

print(
    f"Total REEP players:                  "
    f"{total_players:,}"
)

print(
    f"Players with aliases:                "
    f"{players_with_aliases:,}"
)

print(
    f"Players without aliases:             "
    f"{players_without_aliases:,}"
)

print(
    f"Alias coverage:                      "
    f"{pct(players_with_aliases, total_players):.2f}%"
)

print()
print(
    f"Exact alias collision groups:        "
    f"{len(exact_collision_groups):,}"
)

print(
    f"Players in exact collisions:         "
    f"{len(exact_collision_players):,}"
)

print(
    f"Normalized collision groups:         "
    f"{len(normalized_collision_groups):,}"
)

print(
    f"Players in normalized collisions:   "
    f"{len(normalized_collision_players):,}"
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
    f"{missing_gender_groups:,}"
)

print()
print(
    f"Shared-QID collision groups:          "
    f"{shared_qid_groups:,}"
)

print(
    f"Different-QID collision groups:       "
    f"{different_qid_groups:,}"
)

print(
    f"No-QID collision groups:              "
    f"{no_qid_groups:,}"
)

print()
print(
    f"Provider-name alias players:          "
    f"{len(provider_name_players):,}"
)

print(
    f"Short-alias players:                  "
    f"{len(short_alias_players):,}"
)


# ============================================================
# PLAYER CSV
# ============================================================

print_header("WRITING PLAYER-LEVEL CSV")

with PLAYER_CSV.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "reep_id",
        "label",
        "status",
        "gender",
        "alias_count",
        "exact_collision_count",
        "normalized_collision_count",
        "alias_identity_profile",
        "exact_collision_aliases",
        "normalized_collision_groups",
        "qid_count",
        "qid_values",
        "external_id_count",
        "external_id_values",
        "provider_name_alias",
        "short_alias",
    ])

    for rid in sorted(player_map):

        player = player_map[rid]

        profile = player_identity_profiles[rid]

        qids = sorted(
            player_qids.get(rid, set())
        )

        xids = sorted(
            player_xids.get(rid, set())
        )

        writer.writerow([
            rid,
            player["label"],
            player["status"],
            player["gender"],
            profile["alias_count"],
            profile["exact_collision_count"],
            profile["normalized_collision_count"],
            profile["profile"],
            "|".join(
                profile["exact_collision_aliases"]
            ),
            "|".join(
                str(x)
                for x in profile[
                    "normalized_collision_groups"
                ]
            ),
            len(qids),
            "|".join(qids),
            len(xids),
            "|".join(
                f"{provider}:{external_id}"
                for provider, external_id in xids
            ),
            "yes"
            if rid in provider_name_players
            else "no",
            "yes"
            if rid in short_alias_players
            else "no",
        ])

print()
print(f"Player CSV written:")
print(f"  {PLAYER_CSV}")


# ============================================================
# GROUP CSV
# ============================================================

print_header("WRITING ALIAS COLLISION GROUP CSV")

with GROUP_CSV.open(
    "w",
    newline="",
    encoding="utf-8-sig"
) as f:

    writer = csv.writer(f)

    writer.writerow([
        "group_id",
        "normalized_alias",
        "member_count",
        "reep_ids",
        "labels",
        "label_relationship",
        "genders",
        "gender_relationship",
        "qids",
        "qid_relationship",
        "external_ids",
        "external_id_relationship",
        "statuses",
        "status_relationship",
    ])

    for record in group_records:

        writer.writerow([
            record["group_id"],
            record["normalized_alias"],
            record["member_count"],
            record["reep_ids"],
            record["labels"],
            record["label_relationship"],
            record["genders"],
            record["gender_relationship"],
            record["qids"],
            record["qid_relationship"],
            record["external_ids"],
            record["external_id_relationship"],
            record["statuses"],
            record["status_relationship"],
        ])

print()
print(f"Group CSV written:")
print(f"  {GROUP_CSV}")


# ============================================================
# JSON SUMMARY
# ============================================================

print_header("WRITING JSON SUMMARY")

summary = {
    "audit": "REEP PLAYER ALIAS IDENTITY AUDIT",
    "generated_at_utc": datetime.now(
        timezone.utc
    ).isoformat(),

    "source_database": str(DB_PATH),

    "read_only": True,

    "players": {
        "total": total_players,
        "with_aliases": players_with_aliases,
        "without_aliases": players_without_aliases,
        "alias_coverage_percent": pct(
            players_with_aliases,
            total_players
        ),
    },

    "aliases": {
        "total_rows": len(alias_rows),
        "exact_collision_groups": len(
            exact_collision_groups
        ),
        "exact_collision_players": len(
            exact_collision_players
        ),
        "normalized_collision_groups": len(
            normalized_collision_groups
        ),
        "normalized_collision_players": len(
            normalized_collision_players
        ),
        "maximum_players_per_normalized_alias": (
            max(
                (
                    len(group)
                    for group
                    in normalized_collision_groups.values()
                ),
                default=0
            )
        ),
    },

    "collision_relationships": {
        "same_label_groups": same_label_groups,
        "different_label_groups": different_label_groups,
        "same_gender_groups": same_gender_groups,
        "different_gender_groups": different_gender_groups,
        "no_gender_groups": missing_gender_groups,
        "shared_qid_groups": shared_qid_groups,
        "different_qid_groups": different_qid_groups,
        "no_qid_groups": no_qid_groups,
        "shared_external_id_groups": (
            shared_external_id_groups
        ),
        "different_external_id_groups": (
            different_external_id_groups
        ),
        "no_external_id_groups": (
            no_external_id_groups
        ),
        "same_status_groups": same_status_groups,
        "mixed_status_groups": mixed_status_groups,
    },

    "alias_types": {
        "players_with_provider_name_alias": len(
            provider_name_players
        ),
        "players_with_short_alias": len(
            short_alias_players
        ),
    },

    "player_profiles": dict(
        profile_counts
    ),

    "output_files": {
        "player_csv": str(PLAYER_CSV),
        "group_csv": str(GROUP_CSV),
        "json": str(JSON_OUTPUT),
    },
}

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

print()
print(f"JSON written:")
print(f"  {JSON_OUTPUT}")


# ============================================================
# COMPLETE
# ============================================================

print_header("PLAYER ALIAS IDENTITY AUDIT COMPLETE")

print()
print(
    f"REEP players audited:               "
    f"{total_players:,}"
)

print(
    f"Players with aliases:                "
    f"{players_with_aliases:,}"
)

print(
    f"Normalized alias collision groups:   "
    f"{len(normalized_collision_groups):,}"
)

print(
    f"Players in alias collision groups:   "
    f"{len(normalized_collision_players):,}"
)

print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")

print()
print("Output files:")
print(f"  {PLAYER_CSV}")
print(f"  {GROUP_CSV}")
print(f"  {JSON_OUTPUT}")

con.close()