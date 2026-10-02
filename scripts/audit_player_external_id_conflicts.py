from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import duckdb


# ============================================================
# REEP PLAYER EXTERNAL-ID CONFLICT AUDIT
# ============================================================
#
# READ-ONLY AUDIT
#
# Purpose:
#   Investigate external-ID collisions among REEP players.
#
# Focus:
#   1. Exact provider + property + external_id collisions
#   2. Provider + external_id collisions
#   3. Whether collisions involve:
#      - same/different labels
#      - same/different gender
#      - same/shared QID
#      - same/different DOB status
#      - different properties
#
# Source database is NEVER modified.
# ============================================================


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main\data"
    r"\reep-register-v1.duckdb"
)

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = REPO_ROOT / "output"

CSV_PATH = OUTPUT_DIR / "reep-player-external-id-conflicts.csv"
GROUP_CSV_PATH = OUTPUT_DIR / "reep-external-id-conflict-groups.csv"
JSON_PATH = OUTPUT_DIR / "reep-player-external-id-conflicts.json"


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def normalize_label(value: str | None) -> str:
    if value is None:
        return ""

    value = value.lower().strip()

    # Remove punctuation.
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)

    # Collapse whitespace.
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def safe_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def unique_sorted(values) -> list[str]:
    cleaned = {
        safe_str(v).strip()
        for v in values
        if v is not None and safe_str(v).strip() != ""
    }
    return sorted(cleaned, key=str.lower)


def classify_values(values) -> str:
    values = unique_sorted(values)

    if not values:
        return "none"

    if len(values) == 1:
        return "single"

    return "multiple"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main() -> None:

    print("=" * 70)
    print("REEP PLAYER EXTERNAL-ID CONFLICT AUDIT")
    print("=" * 70)
    print()
    print("READ-ONLY — source database will NOT be modified.")
    print()
    print(f"Source database:")
    print(SOURCE_DB)
    print()

    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Source database not found:\n{SOURCE_DB}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # CONNECT READ-ONLY
    # --------------------------------------------------------

    print("Opening REEP database READ-ONLY...")

    con = duckdb.connect(
        str(SOURCE_DB),
        read_only=True,
    )

    print("Connected successfully.")
    print()

    try:

        # ----------------------------------------------------
        # CHECK REQUIRED TABLES
        # ----------------------------------------------------

        print("=" * 70)
        print("CHECKING REQUIRED TABLES")
        print("=" * 70)

        tables = {
            row[0]
            for row in con.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                """
            ).fetchall()
        }

        required_tables = {
            "players",
            "overlay_xids",
        }

        missing = required_tables - tables

        for table in sorted(required_tables):
            if table in tables:
                print(f"  {table:<20} FOUND")
            else:
                print(f"  {table:<20} MISSING")

        if missing:
            raise RuntimeError(
                "Required table(s) missing: "
                + ", ".join(sorted(missing))
            )

        print()

        # ----------------------------------------------------
        # PLAYER MASTER
        # ----------------------------------------------------

        print("Loading REEP player master...")

        player_rows = con.execute(
            """
            SELECT
                reep_id,
                label,
                status,
                gender
            FROM players
            """
        ).fetchall()

        players = {}

        for reep_id, label, status, gender in player_rows:
            players[safe_str(reep_id)] = {
                "reep_id": safe_str(reep_id),
                "label": safe_str(label),
                "status": safe_str(status),
                "gender": safe_str(gender),
                "normalized_label": normalize_label(label),
            }

        total_players = len(players)

        print(f"  Total REEP players: {total_players:,}")
        print()

        # ----------------------------------------------------
        # XID DATA
        # ----------------------------------------------------

        print("Loading player-linked external IDs...")

        xid_rows = con.execute(
            """
            SELECT
                x.reep_id,
                x.provider,
                x.property,
                x.external_id,
                x.rank,
                x.confidence,
                x.dob_check,
                x.qid
            FROM overlay_xids x
            INNER JOIN players p
                ON x.reep_id = p.reep_id
            WHERE x.external_id IS NOT NULL
              AND TRIM(CAST(x.external_id AS VARCHAR)) <> ''
            """
        ).fetchall()

        total_xid_rows = len(xid_rows)

        print(f"  Player-linked XID rows: {total_xid_rows:,}")
        print()

        # ----------------------------------------------------
        # GROUP XIDS
        # ----------------------------------------------------

        exact_groups = defaultdict(list)
        provider_groups = defaultdict(list)

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

            reep_id = safe_str(reep_id)
            provider = safe_str(provider)
            property_name = safe_str(property_name)
            external_id = safe_str(external_id)

            record = {
                "reep_id": reep_id,
                "provider": provider,
                "property": property_name,
                "external_id": external_id,
                "rank": rank,
                "confidence": confidence,
                "dob_check": safe_str(dob_check),
                "qid": safe_str(qid),
            }

            exact_key = (
                provider,
                property_name,
                external_id,
            )

            provider_key = (
                provider,
                external_id,
            )

            exact_groups[exact_key].append(record)
            provider_groups[provider_key].append(record)

        # ----------------------------------------------------
        # IDENTIFY COLLISIONS
        # ----------------------------------------------------

        exact_collision_groups = {
            key: rows
            for key, rows in exact_groups.items()
            if len({r["reep_id"] for r in rows}) > 1
        }

        provider_collision_groups = {
            key: rows
            for key, rows in provider_groups.items()
            if len({r["reep_id"] for r in rows}) > 1
        }

        # ----------------------------------------------------
        # BUILD CONFLICT RECORDS
        # ----------------------------------------------------

        player_conflicts = {}
        group_records = []

        exact_group_count = 0
        provider_group_count = 0
        cross_property_group_count = 0

        exact_players = set()
        provider_players = set()

        same_label_groups = 0
        different_label_groups = 0

        same_gender_groups = 0
        different_gender_groups = 0

        shared_qid_groups = 0
        different_qid_groups = 0

        same_dob_status_groups = 0
        mixed_dob_status_groups = 0

        for provider_key, rows in provider_collision_groups.items():

            provider, external_id = provider_key

            player_ids = sorted(
                {
                    r["reep_id"]
                    for r in rows
                }
            )

            if len(player_ids) <= 1:
                continue

            provider_group_count += 1
            provider_players.update(player_ids)

            properties = unique_sorted(
                r["property"]
                for r in rows
            )

            qids = unique_sorted(
                r["qid"]
                for r in rows
            )

            dob_statuses = unique_sorted(
                r["dob_check"]
                for r in rows
            )

            labels = [
                players[pid]["label"]
                for pid in player_ids
                if pid in players
            ]

            normalized_labels = unique_sorted(
                normalize_label(label)
                for label in labels
            )

            genders = unique_sorted(
                players[pid]["gender"]
                for pid in player_ids
                if pid in players
            )

            exact_keys = unique_sorted(
                f"{r['provider']}|{r['property']}|{r['external_id']}"
                for r in rows
            )

            is_cross_property = len(properties) > 1

            if is_cross_property:
                cross_property_group_count += 1

            if len(normalized_labels) == 1:
                same_label_groups += 1
                label_relation = "same_normalized_label"
            else:
                different_label_groups += 1
                label_relation = "different_normalized_labels"

            if len(genders) <= 1:
                same_gender_groups += 1
                gender_relation = "same_or_missing_gender"
            else:
                different_gender_groups += 1
                gender_relation = "different_gender"

            if len(qids) == 1 and qids[0] != "":
                shared_qid_groups += 1
                qid_relation = "shared_qid"
            elif len(qids) == 0:
                qid_relation = "no_qid"
            else:
                different_qid_groups += 1
                qid_relation = "different_qids"

            if len(dob_statuses) <= 1:
                same_dob_status_groups += 1
                dob_relation = (
                    "same_dob_status"
                    if dob_statuses
                    else "no_dob_status"
                )
            else:
                mixed_dob_status_groups += 1
                dob_relation = "mixed_dob_status"

            # Determine whether this provider+ID group also
            # contains an exact provider+property+ID collision.
            exact_keys_with_multiple_players = []

            local_exact = defaultdict(set)

            for r in rows:
                key = (
                    r["provider"],
                    r["property"],
                    r["external_id"],
                )
                local_exact[key].add(r["reep_id"])

            for key, ids in local_exact.items():
                if len(ids) > 1:
                    exact_keys_with_multiple_players.append(
                        "|".join(key)
                    )

            has_exact_collision = (
                len(exact_keys_with_multiple_players) > 0
            )

            if has_exact_collision:
                exact_group_count += len(
                    exact_keys_with_multiple_players
                )
                exact_players.update(player_ids)

                conflict_type = "exact_id_collision"
            elif is_cross_property:
                conflict_type = "cross_property_collision"
            else:
                conflict_type = "provider_id_collision"

            group_id = (
                f"{provider}|{external_id}"
            )

            group_record = {
                "group_id": group_id,
                "provider": provider,
                "external_id": external_id,
                "conflict_type": conflict_type,
                "player_count": len(player_ids),
                "players": player_ids,
                "labels": labels,
                "properties": properties,
                "exact_keys": exact_keys,
                "exact_collision_keys": exact_keys_with_multiple_players,
                "label_relation": label_relation,
                "gender_relation": gender_relation,
                "qid_relation": qid_relation,
                "dob_relation": dob_relation,
                "qids": qids,
                "dob_statuses": dob_statuses,
            }

            group_records.append(group_record)

            # -----------------------------------------------
            # PLAYER-LEVEL RECORDS
            # -----------------------------------------------

            for pid in player_ids:

                player = players.get(pid)

                if player is None:
                    continue

                existing = player_conflicts.setdefault(
                    pid,
                    {
                        "reep_id": pid,
                        "label": player["label"],
                        "status": player["status"],
                        "gender": player["gender"],
                        "normalized_label": player[
                            "normalized_label"
                        ],
                        "provider_collision_groups": 0,
                        "exact_collision_groups": 0,
                        "cross_property_groups": 0,
                        "conflict_types": set(),
                        "providers": set(),
                        "external_ids": set(),
                        "properties": set(),
                        "other_players": set(),
                        "other_labels": set(),
                        "qids": set(),
                        "dob_statuses": set(),
                    },
                )

                existing["provider_collision_groups"] += 1
                existing["conflict_types"].add(
                    conflict_type
                )
                existing["providers"].add(provider)
                existing["external_ids"].add(external_id)

                for prop in properties:
                    existing["properties"].add(prop)

                for other_pid in player_ids:
                    if other_pid != pid:
                        existing["other_players"].add(
                            other_pid
                        )

                for label in labels:
                    if label != player["label"]:
                        existing["other_labels"].add(label)

                for qid in qids:
                    if qid:
                        existing["qids"].add(qid)

                for dob_status in dob_statuses:
                    if dob_status:
                        existing["dob_statuses"].add(
                            dob_status
                        )

                if has_exact_collision:
                    existing["exact_collision_groups"] += len(
                        exact_keys_with_multiple_players
                    )

                if is_cross_property:
                    existing["cross_property_groups"] += 1

        # ----------------------------------------------------
        # WRITE GROUP CSV
        # ----------------------------------------------------

        print("=" * 70)
        print("CONFLICT SUMMARY")
        print("=" * 70)

        print(
            f"  Provider+external-ID collision groups: "
            f"{provider_group_count:,}"
        )

        print(
            f"  Players involved in provider+ID collisions: "
            f"{len(provider_players):,}"
        )

        print(
            f"  Exact provider+property+ID collision groups: "
            f"{exact_group_count:,}"
        )

        print(
            f"  Players involved in exact collisions: "
            f"{len(exact_players):,}"
        )

        print(
            f"  Cross-property collision groups: "
            f"{cross_property_group_count:,}"
        )

        print()

        print(
            f"  Same normalized-label groups: "
            f"{same_label_groups:,}"
        )

        print(
            f"  Different normalized-label groups: "
            f"{different_label_groups:,}"
        )

        print(
            f"  Same/missing-gender groups: "
            f"{same_gender_groups:,}"
        )

        print(
            f"  Different-gender groups: "
            f"{different_gender_groups:,}"
        )

        print(
            f"  Shared-QID groups: "
            f"{shared_qid_groups:,}"
        )

        print(
            f"  Different-QID groups: "
            f"{different_qid_groups:,}"
        )

        print(
            f"  Same-DOB-status groups: "
            f"{same_dob_status_groups:,}"
        )

        print(
            f"  Mixed-DOB-status groups: "
            f"{mixed_dob_status_groups:,}"
        )

        print()

        # ----------------------------------------------------
        # GROUP CSV
        # ----------------------------------------------------

        group_fields = [
            "group_id",
            "provider",
            "external_id",
            "conflict_type",
            "player_count",
            "players",
            "labels",
            "properties",
            "exact_keys",
            "exact_collision_keys",
            "label_relation",
            "gender_relation",
            "qid_relation",
            "dob_relation",
            "qids",
            "dob_statuses",
        ]

        with GROUP_CSV_PATH.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=group_fields,
            )

            writer.writeheader()

            for record in sorted(
                group_records,
                key=lambda x: (
                    x["conflict_type"],
                    x["provider"],
                    x["external_id"],
                ),
            ):

                row = dict(record)

                for field in [
                    "players",
                    "labels",
                    "properties",
                    "exact_keys",
                    "exact_collision_keys",
                    "qids",
                    "dob_statuses",
                ]:
                    row[field] = json.dumps(
                        row[field],
                        ensure_ascii=False,
                    )

                writer.writerow(row)

        # ----------------------------------------------------
        # PLAYER CSV
        # ----------------------------------------------------

        player_fields = [
            "reep_id",
            "label",
            "status",
            "gender",
            "normalized_label",
            "provider_collision_groups",
            "exact_collision_groups",
            "cross_property_groups",
            "conflict_types",
            "providers",
            "external_ids",
            "properties",
            "other_players",
            "other_labels",
            "qids",
            "dob_statuses",
        ]

        with CSV_PATH.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=player_fields,
            )

            writer.writeheader()

            for pid in sorted(
                player_conflicts,
                key=lambda x: (
                    player_conflicts[x]["label"].lower(),
                    x,
                ),
            ):

                record = player_conflicts[pid]

                row = {
                    "reep_id": record["reep_id"],
                    "label": record["label"],
                    "status": record["status"],
                    "gender": record["gender"],
                    "normalized_label": record[
                        "normalized_label"
                    ],
                    "provider_collision_groups": record[
                        "provider_collision_groups"
                    ],
                    "exact_collision_groups": record[
                        "exact_collision_groups"
                    ],
                    "cross_property_groups": record[
                        "cross_property_groups"
                    ],
                    "conflict_types": json.dumps(
                        sorted(record["conflict_types"])
                    ),
                    "providers": json.dumps(
                        sorted(record["providers"])
                    ),
                    "external_ids": json.dumps(
                        sorted(record["external_ids"])
                    ),
                    "properties": json.dumps(
                        sorted(record["properties"])
                    ),
                    "other_players": json.dumps(
                        sorted(record["other_players"])
                    ),
                    "other_labels": json.dumps(
                        sorted(record["other_labels"])
                    ),
                    "qids": json.dumps(
                        sorted(record["qids"])
                    ),
                    "dob_statuses": json.dumps(
                        sorted(record["dob_statuses"])
                    ),
                }

                writer.writerow(row)

        # ----------------------------------------------------
        # JSON SUMMARY
        # ----------------------------------------------------

        conflict_type_counts = Counter(
            record["conflict_type"]
            for record in group_records
        )

        summary = {
            "audit": "REEP PLAYER EXTERNAL-ID CONFLICT AUDIT",
            "generated_at_utc": now_utc(),
            "read_only": True,
            "source_database": str(SOURCE_DB),
            "output_files": {
                "player_csv": str(CSV_PATH),
                "group_csv": str(GROUP_CSV_PATH),
                "json": str(JSON_PATH),
            },
            "totals": {
                "players": total_players,
                "player_linked_xid_rows": total_xid_rows,
                "provider_external_id_collision_groups":
                    provider_group_count,
                "players_in_provider_external_id_collisions":
                    len(provider_players),
                "exact_provider_property_external_id_collision_groups":
                    exact_group_count,
                "players_in_exact_collisions":
                    len(exact_players),
                "cross_property_collision_groups":
                    cross_property_group_count,
            },
            "relationship_analysis": {
                "same_normalized_label_groups":
                    same_label_groups,
                "different_normalized_label_groups":
                    different_label_groups,
                "same_or_missing_gender_groups":
                    same_gender_groups,
                "different_gender_groups":
                    different_gender_groups,
                "shared_qid_groups":
                    shared_qid_groups,
                "different_qid_groups":
                    different_qid_groups,
                "same_dob_status_groups":
                    same_dob_status_groups,
                "mixed_dob_status_groups":
                    mixed_dob_status_groups,
            },
            "conflict_type_counts": dict(
                conflict_type_counts
            ),
        }

        with JSON_PATH.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                summary,
                f,
                indent=2,
                ensure_ascii=False,
            )

        # ----------------------------------------------------
        # FINAL
        # ----------------------------------------------------

        print("=" * 70)
        print("OUTPUT")
        print("=" * 70)

        print(f"  Player CSV:")
        print(f"    {CSV_PATH}")

        print(f"  Group CSV:")
        print(f"    {GROUP_CSV_PATH}")

        print(f"  JSON summary:")
        print(f"    {JSON_PATH}")

        print()

        print("=" * 70)
        print("AUDIT COMPLETE")
        print("=" * 70)
        print()
        print("Source database was NOT modified.")

    finally:
        con.close()


if __name__ == "__main__":
    main()