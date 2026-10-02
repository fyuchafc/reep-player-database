import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import duckdb


# ============================================================
# REEP PLAYER ALIAS QUALITY AUDIT
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

CSV_PATH = OUTPUT_DIR / "reep-player-alias-quality.csv"
JSON_PATH = OUTPUT_DIR / "reep-player-alias-quality.json"


print("=" * 70)
print("REEP PLAYER ALIAS QUALITY AUDIT")
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
# main.players is already the player table.
# It does NOT contain entity_type.
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
# LOAD ALIASES
# ============================================================

print("Loading player aliases...")

aliases = con.execute("""
    SELECT
        reep_id,
        alias,
        kind,
        rank,
        language
    FROM main.aliases
""").fetchall()

print(f"  Total alias rows: {len(aliases):,}")
print()


# ============================================================
# CHECK WHICH ALIASES BELONG TO ACTUAL PLAYERS
# ============================================================

print("Checking alias references...")

invalid_references = [
    row
    for row in aliases
    if row[0] not in player_ids
]

player_aliases = [
    row
    for row in aliases
    if row[0] in player_ids
]

print(
    f"  Alias rows belonging to REEP players: "
    f"{len(player_aliases):,}"
)

print(
    f"  Alias rows referencing non-player entities: "
    f"{len(invalid_references):,}"
)
print()


# ============================================================
# GROUP PLAYER ALIASES
# ============================================================

aliases_by_player = defaultdict(list)

for row in player_aliases:
    aliases_by_player[row[0]].append(row)


# ============================================================
# BASIC COVERAGE
# ============================================================

print("Analyzing alias coverage...")

players_with_aliases = len(aliases_by_player)
players_without_aliases = len(players) - players_with_aliases

print(f"  Total REEP players:          {len(players):,}")
print(f"  Players with aliases:        {players_with_aliases:,}")
print(f"  Players without aliases:     {players_without_aliases:,}")

coverage = (
    players_with_aliases / len(players) * 100
    if players
    else 0
)

print(f"  Alias coverage:              {coverage:.2f}%")
print()


# ============================================================
# ALIASES PER PLAYER
# ============================================================

print("Analyzing aliases per player...")

alias_count_distribution = Counter(
    len(rows)
    for rows in aliases_by_player.values()
)

for count in sorted(alias_count_distribution):
    print(
        f"  {count} alias row(s): "
        f"{alias_count_distribution[count]:,} players"
    )

max_aliases = (
    max(alias_count_distribution)
    if alias_count_distribution
    else 0
)

players_with_many_aliases = sum(
    count
    for aliases_count, count in alias_count_distribution.items()
    if aliases_count >= 10
)

print()
print(f"  Maximum aliases for one player: {max_aliases:,}")
print(
    f"  Players with 10+ aliases: "
    f"{players_with_many_aliases:,}"
)
print()


# ============================================================
# ALIAS KIND DISTRIBUTION
# ============================================================

print("Analyzing alias kinds...")

kind_counter = Counter(
    row[2] if row[2] is not None else "<NULL>"
    for row in player_aliases
)

for kind, count in kind_counter.most_common():
    print(f"  {kind}: {count:,}")

print()


# ============================================================
# LANGUAGE DISTRIBUTION
# ============================================================

print("Analyzing alias languages...")

language_counter = Counter(
    row[4] if row[4] is not None else "<NULL>"
    for row in player_aliases
)

for language, count in language_counter.most_common():
    print(f"  {language}: {count:,}")

print()


# ============================================================
# ALIAS RANK DISTRIBUTION
# ============================================================

print("Analyzing alias ranks...")

rank_counter = Counter(
    row[3] if row[3] is not None else "<NULL>"
    for row in player_aliases
)

for rank, count in sorted(
    rank_counter.items(),
    key=lambda x: (
        999999 if isinstance(x[0], str) else x[0]
    )
):
    print(f"  {rank}: {count:,}")

print()


# ============================================================
# NULL / EMPTY ALIASES
# ============================================================

print("Checking alias values...")

null_aliases = sum(
    1
    for row in player_aliases
    if row[1] is None
)

empty_aliases = sum(
    1
    for row in player_aliases
    if row[1] is not None
    and not str(row[1]).strip()
)

print(f"  NULL aliases:  {null_aliases:,}")
print(f"  Empty aliases: {empty_aliases:,}")
print()


# ============================================================
# EXACT DUPLICATES
# ============================================================

print("Checking duplicate alias rows within players...")

player_alias_exact_counter = Counter(
    (
        row[0],
        row[1],
        row[2],
        row[3],
        row[4],
    )
    for row in player_aliases
)

duplicate_exact_rows = sum(
    count - 1
    for count in player_alias_exact_counter.values()
    if count > 1
)

duplicate_exact_groups = sum(
    1
    for count in player_alias_exact_counter.values()
    if count > 1
)

print(
    f"  Exact duplicate groups: "
    f"{duplicate_exact_groups:,}"
)

print(
    f"  Exact duplicate rows beyond first: "
    f"{duplicate_exact_rows:,}"
)
print()


# ============================================================
# NORMALIZED ALIAS COLLISIONS
# ============================================================

print("Analyzing normalized alias collisions...")


def normalize_name(value):
    if value is None:
        return ""

    text = str(value).strip().lower()

    # Collapse repeated whitespace.
    text = " ".join(text.split())

    return text


normalized_alias_players = defaultdict(set)

for row in player_aliases:

    alias = normalize_name(row[1])

    if alias:
        normalized_alias_players[alias].add(row[0])


collision_groups = {
    alias: player_set
    for alias, player_set in normalized_alias_players.items()
    if len(player_set) > 1
}

collision_player_count = sum(
    len(player_set)
    for player_set in collision_groups.values()
)

print(
    f"  Distinct normalized aliases: "
    f"{len(normalized_alias_players):,}"
)

print(
    f"  Normalized alias collision groups: "
    f"{len(collision_groups):,}"
)

print(
    f"  Player memberships in collision groups: "
    f"{collision_player_count:,}"
)
print()


# ============================================================
# SAME-LABEL / DIFFERENT-LABEL COLLISIONS
# ============================================================

print("Analyzing collision types...")

same_label_collision_groups = 0
different_label_collision_groups = 0

for alias, ids in collision_groups.items():

    labels = {
        player_map[player_id][2]
        for player_id in ids
        if player_id in player_map
    }

    if len(labels) <= 1:
        same_label_collision_groups += 1
    else:
        different_label_collision_groups += 1

print(
    f"  Same-label collision groups: "
    f"{same_label_collision_groups:,}"
)

print(
    f"  Different-label collision groups: "
    f"{different_label_collision_groups:,}"
)
print()


# ============================================================
# TOP COLLISION ALIASES
# ============================================================

print("Top normalized alias collision groups...")

top_collisions = sorted(
    collision_groups.items(),
    key=lambda x: (-len(x[1]), x[0])
)[:30]

for index, (alias, ids) in enumerate(top_collisions, 1):

    labels = []

    for player_id in sorted(ids):

        if player_id in player_map:
            labels.append(player_map[player_id][2])

    print()
    print(
        f"  {index}. {alias} "
        f"| players={len(ids)}"
    )

    for label in labels:
        print(f"       {label}")

print()


# ============================================================
# ALIAS KINDS PER PLAYER
# ============================================================

print("Analyzing players with multiple alias kinds...")

player_kinds = defaultdict(set)

for row in player_aliases:

    kind = (
        row[2]
        if row[2] is not None
        else "<NULL>"
    )

    player_kinds[row[0]].add(kind)


kind_count_distribution = Counter(
    len(kinds)
    for kinds in player_kinds.values()
)

for count in sorted(kind_count_distribution):

    print(
        f"  {count} distinct alias kind(s): "
        f"{kind_count_distribution[count]:,} players"
    )

print()


# ============================================================
# IMPORTANT ALIAS KIND COVERAGE
# ============================================================

provider_name_players = {
    row[0]
    for row in player_aliases
    if row[2] == "provider-name"
}

official_name_players = {
    row[0]
    for row in player_aliases
    if row[2] == "official_name"
}

short_name_players = {
    row[0]
    for row in player_aliases
    if row[2] == "short"
}

print("Important alias-kind player coverage...")

print(
    f"  Players with provider-name: "
    f"{len(provider_name_players):,}"
)

print(
    f"  Players with official_name: "
    f"{len(official_name_players):,}"
)

print(
    f"  Players with short aliases: "
    f"{len(short_name_players):,}"
)

print()


# ============================================================
# BUILD PLAYER-LEVEL CSV
# ============================================================

print("Building player-level alias quality CSV...")

csv_rows = []

for player_id, status, label, gender, country in players:

    player_alias_list = aliases_by_player.get(
        player_id,
        []
    )

    kinds = Counter(
        row[2] if row[2] is not None else "<NULL>"
        for row in player_alias_list
    )

    languages = Counter(
        row[4] if row[4] is not None else "<NULL>"
        for row in player_alias_list
    )

    unique_alias_values = {
        str(row[1]).strip()
        for row in player_alias_list
        if row[1] is not None
        and str(row[1]).strip()
    }

    csv_rows.append([
        player_id,
        status,
        label,
        gender,
        country,
        len(player_alias_list),
        len(unique_alias_values),
        len(kinds),
        "; ".join(
            f"{key}={value}"
            for key, value in sorted(kinds.items())
        ),
        "; ".join(
            f"{key}={value}"
            for key, value in sorted(languages.items())
        ),
    ])


print("Writing player-level alias quality CSV...")

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
        "alias_rows",
        "unique_alias_values",
        "distinct_alias_kinds",
        "alias_kind_distribution",
        "language_distribution",
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
        "with_aliases": players_with_aliases,
        "without_aliases": players_without_aliases,
        "alias_coverage_percent": round(
            coverage,
            2
        ),
    },

    "aliases": {
        "total_rows": len(player_aliases),
        "alias_rows_outside_players": len(
            invalid_references
        ),
        "max_aliases_per_player": max_aliases,
        "players_with_10_plus_aliases":
            players_with_many_aliases,

        "kind_distribution":
            dict(kind_counter),

        "language_distribution":
            dict(language_counter),

        "rank_distribution": {
            str(key): value
            for key, value in rank_counter.items()
        },

        "null_aliases":
            null_aliases,

        "empty_aliases":
            empty_aliases,
    },

    "integrity": {
        "invalid_player_references":
            len(invalid_references),

        "exact_duplicate_groups":
            duplicate_exact_groups,

        "exact_duplicate_rows_beyond_first":
            duplicate_exact_rows,
    },

    "normalized_aliases": {
        "distinct_normalized_aliases":
            len(normalized_alias_players),

        "collision_groups":
            len(collision_groups),

        "player_memberships_in_collision_groups":
            collision_player_count,

        "same_label_collision_groups":
            same_label_collision_groups,

        "different_label_collision_groups":
            different_label_collision_groups,
    },

    "alias_kind_player_coverage": {
        "provider-name":
            len(provider_name_players),

        "official_name":
            len(official_name_players),

        "short":
            len(short_name_players),
    },

    "architecture_conclusion": [
        "reep_id remains the authoritative player identity.",
        "Aliases are preserved as evidence and search variants.",
        "Normalized alias values must not be used as primary identity keys.",
        "Alias collisions must not trigger automatic player merges.",
        "Original alias kind, rank, and language metadata should be preserved.",
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
print("PLAYER ALIAS QUALITY AUDIT COMPLETE")
print("=" * 70)
print()
print("SOURCE DATABASE: UNMODIFIED")
print("AUDIT MODE: READ-ONLY")
print()
print("Output files:")
print(f"  {CSV_PATH}")
print(f"  {JSON_PATH}")
print()