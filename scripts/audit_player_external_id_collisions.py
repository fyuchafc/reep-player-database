import csv
import json
import os
import sys
from collections import Counter, defaultdict

import duckdb


# ============================================================
# REEP PLAYER EXTERNAL-ID COLLISION AUDIT
# ============================================================
#
# READ-ONLY AUDIT
#
# Source:
#   Original REEP DuckDB database
#
# This script does NOT:
#   - modify the source database
#   - merge players
#   - delete players
#   - modify QIDs
#   - modify external IDs
#   - modify existing players.json
#
# Identity key tested:
#   provider + property + external_id
#
# Example:
#   transfermarkt + PXXX + 12345
#
# The same external_id may legitimately exist under:
#   - different providers
#   - different properties
#
# Therefore collisions are evaluated using the complete
# provider + property + external_id key.
# ============================================================


SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = "output"

JSON_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "reep-player-external-id-collision-audit.json"
)

CSV_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "reep-player-external-id-collisions.csv"
)


def safe_value(value):
    if value is None:
        return None
    return str(value)


def normalize_key(value):
    if value is None:
        return ""
    return str(value).strip()


def main():
    print("=" * 70)
    print("REEP PLAYER EXTERNAL-ID COLLISION AUDIT")
    print("=" * 70)
    print()
    print("READ-ONLY — source database will NOT be modified.")
    print()

    if not os.path.exists(SOURCE_DB):
        print("ERROR: Source database not found:")
        print(SOURCE_DB)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("SOURCE DATABASE")
    print("-" * 70)
    print(SOURCE_DB)

    file_size = os.path.getsize(SOURCE_DB)

    print(
        f"File size: {file_size:,} bytes "
        f"({file_size / (1024 * 1024):.2f} MiB)"
    )
    print()

    # --------------------------------------------------------
    # Open database read-only
    # --------------------------------------------------------

    print("OPENING DATABASE READ-ONLY...")
    print()

    con = duckdb.connect(
        SOURCE_DB,
        read_only=True
    )

    # --------------------------------------------------------
    # Verify required tables
    # --------------------------------------------------------

    print("VERIFYING REQUIRED TABLES...")
    print()

    required_tables = [
        "main.players",
        "main.overlay_xids",
    ]

    available_tables = {
        row[0]
        for row in con.execute(
            """
            SELECT table_schema || '.' || table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            """
        ).fetchall()
    }

    for table in required_tables:
        if table not in available_tables:
            print(f"ERROR: Required table missing: {table}")
            con.close()
            sys.exit(1)

    print("Required tables found.")
    print()

    # --------------------------------------------------------
    # Load strict player-only external IDs
    # --------------------------------------------------------

    print("LOADING PLAYER EXTERNAL IDs...")
    print()

    query = """
        SELECT
            x.reep_id,
            p.label,
            p.status,
            p.gender,
            x.provider,
            x.property,
            x.external_id,
            x.rank,
            x.confidence,
            x.dob_check,
            x.qid
        FROM main.overlay_xids x
        INNER JOIN main.players p
            ON p.reep_id = x.reep_id
        WHERE x.external_id IS NOT NULL
          AND TRIM(CAST(x.external_id AS VARCHAR)) <> ''
        ORDER BY
            x.provider,
            x.property,
            x.external_id,
            x.reep_id
    """

    rows = con.execute(query).fetchall()

    print(f"Player external-ID rows: {len(rows):,}")
    print()

    # --------------------------------------------------------
    # Column positions
    # --------------------------------------------------------

    # 0 reep_id
    # 1 label
    # 2 status
    # 3 gender
    # 4 provider
    # 5 property
    # 6 external_id
    # 7 rank
    # 8 confidence
    # 9 dob_check
    # 10 qid

    # --------------------------------------------------------
    # Basic statistics
    # --------------------------------------------------------

    player_ids = {
        row[0]
        for row in rows
    }

    exact_keys = Counter()

    provider_counts = Counter()
    provider_players = defaultdict(set)
    provider_external_ids = defaultdict(set)

    provider_external_id_without_property = Counter()
    provider_external_id_without_property_players = defaultdict(set)

    exact_key_players = defaultdict(set)
    exact_key_rows = defaultdict(list)

    for row in rows:
        (
            reep_id,
            label,
            status,
            gender,
            provider,
            property_name,
            external_id,
            rank,
            confidence,
            dob_check,
            qid,
        ) = row

        provider = normalize_key(provider)
        property_name = normalize_key(property_name)
        external_id = normalize_key(external_id)

        exact_key = (
            provider,
            property_name,
            external_id
        )

        provider_key = (
            provider,
            external_id
        )

        exact_keys[exact_key] += 1

        provider_counts[provider] += 1
        provider_players[provider].add(reep_id)
        provider_external_ids[provider].add(external_id)

        provider_external_id_without_property[provider_key] += 1
        provider_external_id_without_property_players[
            provider_key
        ].add(reep_id)

        exact_key_players[exact_key].add(reep_id)
        exact_key_rows[exact_key].append(row)

    # --------------------------------------------------------
    # Exact collision groups
    # --------------------------------------------------------

    collision_keys = {
        key: players
        for key, players in exact_key_players.items()
        if len(players) > 1
    }

    collision_rows = []

    for key, players in collision_keys.items():
        collision_rows.extend(
            exact_key_rows[key]
        )

    collision_player_ids = {
        row[0]
        for row in collision_rows
    }

    # --------------------------------------------------------
    # Same-label / different-label analysis
    # --------------------------------------------------------

    same_label_groups = 0
    different_label_groups = 0

    collision_group_details = []

    for key in sorted(collision_keys):
        players = sorted(collision_keys[key])
        rows_for_key = exact_key_rows[key]

        labels_by_player = {}

        for row in rows_for_key:
            reep_id = row[0]
            label = row[1]

            labels_by_player.setdefault(
                reep_id,
                set()
            ).add(
                safe_value(label)
            )

        all_labels = set()

        for labels in labels_by_player.values():
            all_labels.update(labels)

        if len(all_labels) <= 1:
            same_label_groups += 1
        else:
            different_label_groups += 1

        qids = {
            safe_value(row[10])
            for row in rows_for_key
            if row[10] is not None
            and str(row[10]).strip() != ""
        }

        confidences = Counter(
            safe_value(row[8])
            for row in rows_for_key
        )

        dob_checks = Counter(
            safe_value(row[9])
            for row in rows_for_key
        )

        statuses = Counter(
            safe_value(row[2])
            for row in rows_for_key
        )

        genders = Counter(
            safe_value(row[3])
            for row in rows_for_key
        )

        collision_group_details.append(
            {
                "provider": key[0],
                "property": key[1],
                "external_id": key[2],
                "reep_player_count": len(players),
                "reep_ids": players,
                "labels": sorted(all_labels),
                "qids": sorted(qids),
                "qid_count": len(qids),
                "same_label": len(all_labels) <= 1,
                "confidence": dict(confidences),
                "dob_check": dict(dob_checks),
                "status": dict(statuses),
                "gender": dict(genders),
            }
        )

    # --------------------------------------------------------
    # Provider + external_id collisions ignoring property
    # --------------------------------------------------------

    provider_external_collision_groups = {
        key: players
        for key, players in provider_external_id_without_property_players.items()
        if len(players) > 1
    }

    # Determine how many of these are explained by different properties
    property_split_groups = 0
    same_property_collision_groups = 0

    for provider_key, players in provider_external_collision_groups.items():

        matching_rows = []

        provider = provider_key[0]
        external_id = provider_key[1]

        for row in rows:
            if (
                normalize_key(row[4]) == provider
                and normalize_key(row[6]) == external_id
            ):
                matching_rows.append(row)

        properties = {
            normalize_key(row[5])
            for row in matching_rows
        }

        if len(properties) > 1:
            property_split_groups += 1
        else:
            same_property_collision_groups += 1

    # --------------------------------------------------------
    # QID consistency inside exact external-ID collision groups
    # --------------------------------------------------------

    qid_conflict_groups = 0
    qid_consistent_groups = 0

    for detail in collision_group_details:
        if detail["qid_count"] > 1:
            qid_conflict_groups += 1
        else:
            qid_consistent_groups += 1

    # --------------------------------------------------------
    # Provider collision summary
    # --------------------------------------------------------

    provider_collision_groups = Counter()
    provider_collision_rows = Counter()
    provider_collision_players = defaultdict(set)

    for detail in collision_group_details:
        provider = detail["provider"]

        provider_collision_groups[provider] += 1
        provider_collision_rows[provider] += (
            detail["reep_player_count"]
        )

        for reep_id in detail["reep_ids"]:
            provider_collision_players[provider].add(
                reep_id
            )

    provider_summary = []

    for provider in sorted(provider_counts):
        provider_summary.append(
            {
                "provider": provider,
                "rows": provider_counts[provider],
                "players": len(provider_players[provider]),
                "distinct_external_ids": len(
                    provider_external_ids[provider]
                ),
                "exact_collision_groups": provider_collision_groups[
                    provider
                ],
                "collision_rows": provider_collision_rows[
                    provider
                ],
                "collision_players": len(
                    provider_collision_players[provider]
                ),
            }
        )

    # --------------------------------------------------------
    # Largest collision groups
    # --------------------------------------------------------

    largest_collision_groups = sorted(
        collision_group_details,
        key=lambda x: (
            -x["reep_player_count"],
            x["provider"],
            x["property"],
            x["external_id"],
        )
    )[:100]

    # --------------------------------------------------------
    # Build JSON audit
    # --------------------------------------------------------

    audit = {
        "audit": {
            "name": "REEP Player External-ID Collision Audit",
            "read_only": True,
            "identity_key": [
                "provider",
                "property",
                "external_id",
            ],
            "source_database": SOURCE_DB,
            "source_file_size_bytes": file_size,
        },

        "totals": {
            "player_external_id_rows": len(rows),
            "players_with_external_ids": len(player_ids),
            "distinct_exact_keys": len(exact_keys),
            "exact_collision_groups": len(collision_keys),
            "exact_collision_rows": len(collision_rows),
            "players_in_exact_collision_groups": len(
                collision_player_ids
            ),
            "same_label_collision_groups": same_label_groups,
            "different_label_collision_groups": different_label_groups,
            "qid_conflict_collision_groups": qid_conflict_groups,
            "qid_consistent_collision_groups": qid_consistent_groups,
            "provider_external_id_collision_groups": len(
                provider_external_collision_groups
            ),
            "provider_external_id_property_split_groups": (
                property_split_groups
            ),
            "provider_external_id_same_property_collision_groups": (
                same_property_collision_groups
            ),
        },

        "providers": provider_summary,

        "collision_groups": collision_group_details,

        "largest_collision_groups": largest_collision_groups,
    }

    # --------------------------------------------------------
    # Write JSON
    # --------------------------------------------------------

    with open(
        JSON_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            audit,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # Write CSV
    # --------------------------------------------------------

    with open(
        CSV_OUTPUT,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            [
                "provider",
                "property",
                "external_id",
                "reep_player_count",
                "reep_ids",
                "labels",
                "qids",
                "qid_count",
                "same_label",
                "confidence",
                "dob_check",
                "status",
                "gender",
            ]
        )

        for detail in collision_group_details:
            writer.writerow(
                [
                    detail["provider"],
                    detail["property"],
                    detail["external_id"],
                    detail["reep_player_count"],
                    "|".join(detail["reep_ids"]),
                    "|".join(detail["labels"]),
                    "|".join(detail["qids"]),
                    detail["qid_count"],
                    detail["same_label"],
                    json.dumps(
                        detail["confidence"],
                        ensure_ascii=False
                    ),
                    json.dumps(
                        detail["dob_check"],
                        ensure_ascii=False
                    ),
                    json.dumps(
                        detail["status"],
                        ensure_ascii=False
                    ),
                    json.dumps(
                        detail["gender"],
                        ensure_ascii=False
                    ),
                ]
            )

    # --------------------------------------------------------
    # Console report
    # --------------------------------------------------------

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    print(
        f"Player external-ID rows:              "
        f"{len(rows):,}"
    )

    print(
        f"Players with external IDs:             "
        f"{len(player_ids):,}"
    )

    print(
        f"Distinct exact provider/property/ID:   "
        f"{len(exact_keys):,}"
    )

    print(
        f"Exact collision groups:                "
        f"{len(collision_keys):,}"
    )

    print(
        f"Exact collision rows:                  "
        f"{len(collision_rows):,}"
    )

    print(
        f"Players in collision groups:           "
        f"{len(collision_player_ids):,}"
    )

    print(
        f"Same-label collision groups:            "
        f"{same_label_groups:,}"
    )

    print(
        f"Different-label collision groups:      "
        f"{different_label_groups:,}"
    )

    print(
        f"QID-conflict collision groups:         "
        f"{qid_conflict_groups:,}"
    )

    print(
        f"QID-consistent collision groups:       "
        f"{qid_consistent_groups:,}"
    )

    print()

    print(
        "Provider + external_id collisions "
        "(property ignored):"
    )

    print(
        f"  Collision groups:                    "
        f"{len(provider_external_collision_groups):,}"
    )

    print(
        f"  Explained by different properties:    "
        f"{property_split_groups:,}"
    )

    print(
        f"  Same-property collisions:             "
        f"{same_property_collision_groups:,}"
    )

    print()

    print("=" * 70)
    print("PROVIDER SUMMARY")
    print("=" * 70)

    for item in provider_summary:
        print(
            f"{item['provider']}: "
            f"rows={item['rows']:,} | "
            f"players={item['players']:,} | "
            f"external_ids={item['distinct_external_ids']:,} | "
            f"collision_groups={item['exact_collision_groups']:,} | "
            f"collision_players={item['collision_players']:,}"
        )

    print()

    print("=" * 70)
    print("LARGEST COLLISION GROUPS")
    print("=" * 70)

    if not largest_collision_groups:
        print("No exact external-ID collision groups found.")
    else:
        for index, detail in enumerate(
            largest_collision_groups[:20],
            start=1
        ):
            print(
                f"{index}. "
                f"{detail['provider']} | "
                f"{detail['property']} | "
                f"{detail['external_id']} | "
                f"players={detail['reep_player_count']} | "
                f"labels={detail['labels']}"
            )

    print()

    print("=" * 70)
    print("OUTPUT FILES")
    print("=" * 70)
    print(JSON_OUTPUT)
    print(CSV_OUTPUT)
    print()

    print("AUDIT COMPLETE")
    print("Source database was opened READ-ONLY.")
    print("No players were merged or deleted.")
    print("No external IDs were modified.")
    print("No QIDs were modified.")

    con.close()


if __name__ == "__main__":
    main()