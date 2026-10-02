import duckdb
import json
import csv
from pathlib import Path
from collections import Counter, defaultdict

# ============================================================
# REEP PLAYER FIELD SOURCES AUDIT
# ============================================================
# READ-ONLY AUDIT
# The source REEP database will NOT be modified.
# ============================================================


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

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

CSV_PATH = OUTPUT_DIR / "reep-player-field-sources.csv"
JSON_PATH = OUTPUT_DIR / "reep-player-field-sources.json"


# ------------------------------------------------------------
# HEADER
# ------------------------------------------------------------

print("=" * 70)
print("REEP PLAYER FIELD SOURCES AUDIT")
print("=" * 70)
print()
print("READ-ONLY — source database will NOT be modified.")
print()
print("Source database:")
print(DB_PATH)
print()


# ------------------------------------------------------------
# CHECK DATABASE
# ------------------------------------------------------------

if not DB_PATH.exists():
    raise FileNotFoundError(
        f"Source database not found:\n{DB_PATH}"
    )


# ------------------------------------------------------------
# CONNECT READ-ONLY
# ------------------------------------------------------------

con = duckdb.connect(
    str(DB_PATH),
    read_only=True
)

print("Connecting to REEP database...")
print("Connected successfully.")
print()


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def table_exists(table_name):
    result = con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
        """,
        [table_name]
    ).fetchone()[0]

    return result > 0


def get_columns(table_name):
    rows = con.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ?
        ORDER BY ordinal_position
        """,
        [table_name]
    ).fetchall()

    return [row[0] for row in rows]


def count_rows(table_name):
    return con.execute(
        f"SELECT COUNT(*) FROM {table_name}"
    ).fetchone()[0]


def column_exists(table_name, column_name):
    return column_name in get_columns(table_name)


# ------------------------------------------------------------
# CHECK PLAYERS TABLE
# ------------------------------------------------------------

print("=" * 70)
print("CHECKING PLAYERS TABLE")
print("=" * 70)

if not table_exists("players"):
    raise RuntimeError(
        "The REEP database does not contain a 'players' table."
    )

player_columns = get_columns("players")

print()
print("Players table columns:")
print(", ".join(player_columns))
print()

required_columns = [
    "reep_id",
    "status",
    "label",
    "gender",
    "country",
]

missing_columns = [
    column
    for column in required_columns
    if column not in player_columns
]

if missing_columns:
    raise RuntimeError(
        "Required columns missing from players table: "
        + ", ".join(missing_columns)
    )


# ------------------------------------------------------------
# LOAD PLAYER MASTER
# ------------------------------------------------------------

print("=" * 70)
print("LOADING PLAYER MASTER")
print("=" * 70)

players = con.execute(
    """
    SELECT
        reep_id,
        status,
        label,
        gender,
        country
    FROM players
    """
).fetchall()

print()
print(f"REEP players loaded: {len(players):,}")
print()


# ------------------------------------------------------------
# PLAYER LOOKUP
# ------------------------------------------------------------

player_lookup = {}

for reep_id, status, label, gender, country in players:
    player_lookup[reep_id] = {
        "reep_id": reep_id,
        "status": status,
        "label": label,
        "gender": gender,
        "country": country,
    }


# ------------------------------------------------------------
# BASIC FIELD COMPLETENESS
# ------------------------------------------------------------

print("=" * 70)
print("PLAYER FIELD COMPLETENESS")
print("=" * 70)

field_stats = {}

for field in required_columns:
    values = [
        player[field]
        for player in player_lookup.values()
    ]

    present = sum(
        1
        for value in values
        if value is not None and str(value).strip() != ""
    )

    missing = len(values) - present

    percentage = (
        present / len(values) * 100
        if values
        else 0
    )

    field_stats[field] = {
        "present": present,
        "missing": missing,
        "coverage_percent": round(percentage, 2),
    }

    print(
        f"{field:<12} "
        f"present={present:>9,} "
        f"missing={missing:>9,} "
        f"coverage={percentage:>6.2f}%"
    )

print()


# ------------------------------------------------------------
# STATUS DISTRIBUTION
# ------------------------------------------------------------

status_counter = Counter(
    player["status"]
    for player in player_lookup.values()
)

print("=" * 70)
print("STATUS SOURCES")
print("=" * 70)

for status, count in status_counter.most_common():
    print(
        f"{str(status):<15} {count:>10,}"
    )

print()


# ------------------------------------------------------------
# GENDER DISTRIBUTION
# ------------------------------------------------------------

gender_counter = Counter(
    player["gender"]
    for player in player_lookup.values()
)

print("=" * 70)
print("GENDER FIELD SOURCES")
print("=" * 70)

for gender, count in gender_counter.most_common():
    print(
        f"{str(gender):<15} {count:>10,}"
    )

print()


# ------------------------------------------------------------
# COUNTRY DISTRIBUTION
# ------------------------------------------------------------

country_counter = Counter(
    player["country"]
    for player in player_lookup.values()
)

print("=" * 70)
print("COUNTRY FIELD SOURCES")
print("=" * 70)

non_null_countries = {
    country: count
    for country, count in country_counter.items()
    if country is not None
}

print(
    f"Players with country: "
    f"{sum(non_null_countries.values()):,}"
)

print(
    f"Players without country: "
    f"{country_counter.get(None, 0):,}"
)

print()


# ------------------------------------------------------------
# ENTITY TABLE
# ------------------------------------------------------------

entity_available = table_exists("entities")

print("=" * 70)
print("ENTITY FIELD SOURCE CHECK")
print("=" * 70)

entity_stats = {}

if entity_available:

    entity_columns = get_columns("entities")

    print()
    print("Entities table columns:")
    print(", ".join(entity_columns))
    print()

    # Determine useful fields dynamically.
    entity_id_column = None

    for candidate in ["reep_id", "entity_id", "id"]:
        if candidate in entity_columns:
            entity_id_column = candidate
            break

    if entity_id_column is None:
        print("No usable entity ID column found.")
        print()

    else:

        print(
            f"Entity ID column detected: "
            f"{entity_id_column}"
        )
        print()

        # Compare fields only when the columns exist.
        comparison_fields = [
            field
            for field in [
                "status",
                "label",
                "gender",
                "country",
            ]
            if field in entity_columns
        ]

        if comparison_fields:

            select_fields = ", ".join(
                [entity_id_column] + comparison_fields
            )

            entity_rows = con.execute(
                f"""
                SELECT {select_fields}
                FROM entities
                WHERE {entity_id_column} IN (
                    SELECT reep_id
                    FROM players
                )
                """
            ).fetchall()

            print(
                f"Entity rows matching players: "
                f"{len(entity_rows):,}"
            )
            print()

            entity_lookup = {}

            for row in entity_rows:

                entity_id = row[0]

                values = {}

                for index, field in enumerate(
                    comparison_fields,
                    start=1
                ):
                    values[field] = row[index]

                entity_lookup[entity_id] = values

            for field in comparison_fields:

                player_present = 0
                entity_present = 0
                matching = 0
                different = 0

                for reep_id, player in player_lookup.items():

                    if reep_id not in entity_lookup:
                        continue

                    player_value = player[field]
                    entity_value = entity_lookup[reep_id][field]

                    if (
                        player_value is not None
                        and str(player_value).strip() != ""
                    ):
                        player_present += 1

                    if (
                        entity_value is not None
                        and str(entity_value).strip() != ""
                    ):
                        entity_present += 1

                    if player_value == entity_value:
                        matching += 1
                    else:
                        different += 1

                entity_stats[field] = {
                    "player_present": player_present,
                    "entity_present": entity_present,
                    "matching": matching,
                    "different": different,
                }

                print(
                    f"{field:<12} "
                    f"entity_present={entity_present:>9,} "
                    f"matching={matching:>9,} "
                    f"different={different:>9,}"
                )

else:
    print("Entities table not found.")

print()


# ------------------------------------------------------------
# OVERLAY LINKS
# ------------------------------------------------------------

overlay_links_available = table_exists("overlay_links")

print("=" * 70)
print("OVERLAY LINK SOURCE CHECK")
print("=" * 70)

overlay_stats = {}

if overlay_links_available:

    overlay_columns = get_columns("overlay_links")

    print()
    print("overlay_links columns:")
    print(", ".join(overlay_columns))
    print()

    print(
        f"Total overlay_links rows: "
        f"{count_rows('overlay_links'):,}"
    )

    # Look for likely player ID columns.
    possible_id_columns = [
        column
        for column in [
            "reep_id",
            "entity_id",
            "player_id",
            "id",
        ]
        if column in overlay_columns
    ]

    print(
        "Possible ID columns: "
        + (
            ", ".join(possible_id_columns)
            if possible_id_columns
            else "none"
        )
    )

    print()

    # Provider/source columns.
    possible_source_columns = [
        column
        for column in [
            "provider",
            "source",
            "source_name",
            "overlay",
            "namespace",
        ]
        if column in overlay_columns
    ]

    if possible_source_columns:

        source_column = possible_source_columns[0]

        source_rows = con.execute(
            f"""
            SELECT
                {source_column},
                COUNT(*)
            FROM overlay_links
            GROUP BY {source_column}
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        print(
            f"Source distribution using '{source_column}':"
        )

        for source, count in source_rows[:20]:
            print(
                f"  {str(source):<25} "
                f"{count:>10,}"
            )

        overlay_stats["source_column"] = source_column
        overlay_stats["sources"] = {
            str(source): count
            for source, count in source_rows
        }

else:
    print("overlay_links table not found.")

print()


# ------------------------------------------------------------
# OVERLAY XIDS
# ------------------------------------------------------------

overlay_xids_available = table_exists("overlay_xids")

print("=" * 70)
print("OVERLAY XID SOURCE CHECK")
print("=" * 70)

xid_stats = {}

if overlay_xids_available:

    xid_columns = get_columns("overlay_xids")

    print()
    print("overlay_xids columns:")
    print(", ".join(xid_columns))
    print()

    print(
        f"Total overlay_xids rows: "
        f"{count_rows('overlay_xids'):,}"
    )

    possible_id_columns = [
        column
        for column in [
            "reep_id",
            "entity_id",
            "player_id",
            "id",
        ]
        if column in xid_columns
    ]

    possible_provider_columns = [
        column
        for column in [
            "provider",
            "source",
            "namespace",
            "platform",
        ]
        if column in xid_columns
    ]

    print(
        "Possible player ID columns: "
        + (
            ", ".join(possible_id_columns)
            if possible_id_columns
            else "none"
        )
    )

    print(
        "Possible provider columns: "
        + (
            ", ".join(possible_provider_columns)
            if possible_provider_columns
            else "none"
        )
    )

    print()

    if possible_provider_columns:

        provider_column = possible_provider_columns[0]

        provider_rows = con.execute(
            f"""
            SELECT
                {provider_column},
                COUNT(*)
            FROM overlay_xids
            GROUP BY {provider_column}
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        print(
            f"Provider distribution using "
            f"'{provider_column}':"
        )

        for provider, count in provider_rows[:20]:
            print(
                f"  {str(provider):<25} "
                f"{count:>10,}"
            )

        xid_stats["provider_column"] = provider_column
        xid_stats["providers"] = {
            str(provider): count
            for provider, count in provider_rows
        }

else:
    print("overlay_xids table not found.")

print()


# ------------------------------------------------------------
# ALIAS SOURCE CHECK
# ------------------------------------------------------------

aliases_available = table_exists("aliases")

print("=" * 70)
print("ALIAS SOURCE CHECK")
print("=" * 70)

alias_stats = {}

if aliases_available:

    alias_columns = get_columns("aliases")

    print()
    print("aliases columns:")
    print(", ".join(alias_columns))
    print()

    print(
        f"Total alias rows: "
        f"{count_rows('aliases'):,}"
    )

    possible_id_columns = [
        column
        for column in [
            "reep_id",
            "entity_id",
            "player_id",
            "id",
        ]
        if column in alias_columns
    ]

    possible_source_columns = [
        column
        for column in [
            "provider",
            "source",
            "namespace",
        ]
        if column in alias_columns
    ]

    print(
        "Possible player ID columns: "
        + (
            ", ".join(possible_id_columns)
            if possible_id_columns
            else "none"
        )
    )

    print(
        "Possible source columns: "
        + (
            ", ".join(possible_source_columns)
            if possible_source_columns
            else "none"
        )
    )

    print()

    if possible_source_columns:

        source_column = possible_source_columns[0]

        alias_source_rows = con.execute(
            f"""
            SELECT
                {source_column},
                COUNT(*)
            FROM aliases
            GROUP BY {source_column}
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        print(
            f"Alias source distribution using "
            f"'{source_column}':"
        )

        for source, count in alias_source_rows[:20]:
            print(
                f"  {str(source):<25} "
                f"{count:>10,}"
            )

        alias_stats["source_column"] = source_column
        alias_stats["sources"] = {
            str(source): count
            for source, count in alias_source_rows
        }

else:
    print("aliases table not found.")

print()


# ------------------------------------------------------------
# OVERLAY ALIAS SOURCE CHECK
# ------------------------------------------------------------

overlay_aliases_available = table_exists(
    "overlay_aliases"
)

print("=" * 70)
print("OVERLAY ALIAS SOURCE CHECK")
print("=" * 70)

overlay_alias_stats = {}

if overlay_aliases_available:

    overlay_alias_columns = get_columns(
        "overlay_aliases"
    )

    print()
    print("overlay_aliases columns:")
    print(", ".join(overlay_alias_columns))
    print()

    print(
        f"Total overlay_alias rows: "
        f"{count_rows('overlay_aliases'):,}"
    )

    possible_source_columns = [
        column
        for column in [
            "provider",
            "source",
            "namespace",
            "overlay",
        ]
        if column in overlay_alias_columns
    ]

    print(
        "Possible source columns: "
        + (
            ", ".join(possible_source_columns)
            if possible_source_columns
            else "none"
        )
    )

    print()

    if possible_source_columns:

        source_column = possible_source_columns[0]

        rows = con.execute(
            f"""
            SELECT
                {source_column},
                COUNT(*)
            FROM overlay_aliases
            GROUP BY {source_column}
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        print(
            f"Overlay alias source distribution "
            f"using '{source_column}':"
        )

        for source, count in rows[:20]:
            print(
                f"  {str(source):<25} "
                f"{count:>10,}"
            )

        overlay_alias_stats[
            "source_column"
        ] = source_column

        overlay_alias_stats[
            "sources"
        ] = {
            str(source): count
            for source, count in rows
        }

else:
    print("overlay_aliases table not found.")

print()


# ------------------------------------------------------------
# BUILD FIELD SOURCE SUMMARY
# ------------------------------------------------------------

print("=" * 70)
print("FIELD SOURCE SUMMARY")
print("=" * 70)

field_source_summary = {}

for field in [
    "reep_id",
    "label",
    "status",
    "gender",
    "country",
]:

    stats = field_stats[field]

    field_source_summary[field] = {
        "player_table_present": stats["present"],
        "player_table_missing": stats["missing"],
        "player_table_coverage_percent":
            stats["coverage_percent"],
    }

    print()
    print(field.upper())

    print(
        f"  Player master present: "
        f"{stats['present']:,}"
    )

    print(
        f"  Player master missing: "
        f"{stats['missing']:,}"
    )

    print(
        f"  Coverage: "
        f"{stats['coverage_percent']:.2f}%"
    )

    if field in entity_stats:

        print(
            f"  Entity present: "
            f"{entity_stats[field]['entity_present']:,}"
        )

        print(
            f"  Entity/player matching: "
            f"{entity_stats[field]['matching']:,}"
        )

        print(
            f"  Entity/player different: "
            f"{entity_stats[field]['different']:,}"
        )


# ------------------------------------------------------------
# CREATE PLAYER-LEVEL SOURCE REPORT
# ------------------------------------------------------------

print()
print("=" * 70)
print("CREATING PLAYER-LEVEL SOURCE REPORT")
print("=" * 70)

csv_rows = []

for reep_id, player in player_lookup.items():

    row = {
        "reep_id": reep_id,
        "label": player["label"],
        "status": player["status"],
        "gender": player["gender"],
        "country": player["country"],
        "gender_source": (
            "players"
            if player["gender"] is not None
            else "missing"
        ),
        "country_source": (
            "players"
            if player["country"] is not None
            else "missing"
        ),
    }

    csv_rows.append(row)


# ------------------------------------------------------------
# WRITE CSV
# ------------------------------------------------------------

with open(
    CSV_PATH,
    "w",
    newline="",
    encoding="utf-8-sig"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=[
            "reep_id",
            "label",
            "status",
            "gender",
            "country",
            "gender_source",
            "country_source",
        ],
    )

    writer.writeheader()
    writer.writerows(csv_rows)


# ------------------------------------------------------------
# BUILD JSON REPORT
# ------------------------------------------------------------

report = {
    "audit": "REEP Player Field Sources Audit",
    "read_only": True,
    "database": str(DB_PATH),

    "player_count": len(players),

    "player_table": {
        "columns": player_columns,
        "field_stats": field_stats,
        "status_distribution": {
            str(key): value
            for key, value in status_counter.items()
        },
        "gender_distribution": {
            str(key): value
            for key, value in gender_counter.items()
        },
        "country_distribution": {
            str(key): value
            for key, value in country_counter.items()
        },
    },

    "entity_source": entity_stats,

    "overlay_links": overlay_stats,

    "overlay_xids": xid_stats,

    "aliases": alias_stats,

    "overlay_aliases": overlay_alias_stats,

    "field_source_summary": field_source_summary,

    "outputs": {
        "csv": str(CSV_PATH),
        "json": str(JSON_PATH),
    },
}


# ------------------------------------------------------------
# WRITE JSON
# ------------------------------------------------------------

with open(
    JSON_PATH,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        report,
        file,
        indent=2,
        ensure_ascii=False,
        default=str,
    )


# ------------------------------------------------------------
# FINAL SUMMARY
# ------------------------------------------------------------

print()
print("=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
print()

print(
    f"REEP players audited: "
    f"{len(players):,}"
)

print()

print(
    f"Gender present: "
    f"{field_stats['gender']['present']:,}"
)

print(
    f"Gender missing: "
    f"{field_stats['gender']['missing']:,}"
)

print(
    f"Country present: "
    f"{field_stats['country']['present']:,}"
)

print(
    f"Country missing: "
    f"{field_stats['country']['missing']:,}"
)

print()

print("Output files:")
print(CSV_PATH)
print(JSON_PATH)

print()
print("=" * 70)

con.close()