import os
import json
from datetime import datetime, timezone

import duckdb


# ============================================================
# PATHS
# ============================================================

SOURCE_ROOT = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
)

REPO_ROOT = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\reep-player-database-main"
)

DB_PATH = os.path.join(
    SOURCE_ROOT,
    "data",
    "reep-register-v1.duckdb"
)

OUTPUT_DIR = os.path.join(REPO_ROOT, "output")

CSV_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-status-identity.csv"
)

JSON_PATH = os.path.join(
    OUTPUT_DIR,
    "reep-player-status-identity.json"
)


# ============================================================
# HELPERS
# ============================================================

def normalize_id(value):
    if value is None:
        return None
    return str(value).strip()


def normalize_label(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def print_section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

def main():

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("REEP PLAYER STATUS IDENTITY AUDIT")
    print("=" * 70)
    print()
    print("READ-ONLY — source database will NOT be modified.")
    print()
    print("Source database:")
    print(DB_PATH)

    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Source database not found:\n{DB_PATH}"
        )

    print()
    print("Opening REEP database READ-ONLY...")

    con = duckdb.connect(DB_PATH, read_only=True)

    print("Connected successfully.")

    # --------------------------------------------------------
    # REQUIRED TABLES
    # --------------------------------------------------------

    print_section("CHECKING REQUIRED TABLES")

    tables = {
        row[0]
        for row in con.execute(
            "SHOW TABLES"
        ).fetchall()
    }

    required_tables = {"players", "redirects"}

    missing_tables = required_tables - tables

    for table in sorted(required_tables):
        if table in tables:
            print(f"  {table:<20} FOUND")
        else:
            print(f"  {table:<20} MISSING")

    if missing_tables:
        raise RuntimeError(
            "Required table(s) missing: "
            + ", ".join(sorted(missing_tables))
        )

    # --------------------------------------------------------
    # CHECK PLAYER SCHEMA
    # --------------------------------------------------------

    print_section("CHECKING PLAYER SCHEMA")

    player_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE players"
        ).fetchall()
    ]

    required_player_columns = {
        "reep_id",
        "label",
        "status",
    }

    missing_player_columns = (
        required_player_columns - set(player_columns)
    )

    for column in sorted(required_player_columns):
        if column in player_columns:
            print(f"  {column:<20} FOUND")
        else:
            print(f"  {column:<20} MISSING")

    if missing_player_columns:
        raise RuntimeError(
            "Required player column(s) missing: "
            + ", ".join(sorted(missing_player_columns))
        )

    # --------------------------------------------------------
    # CHECK REDIRECT SCHEMA
    # --------------------------------------------------------

    redirect_columns = [
        row[0]
        for row in con.execute(
            "DESCRIBE redirects"
        ).fetchall()
    ]

    required_redirect_columns = {
        "from_id",
        "to_id",
        "reason",
    }

    missing_redirect_columns = (
        required_redirect_columns - set(redirect_columns)
    )

    for column in sorted(required_redirect_columns):
        if column in redirect_columns:
            print(f"  redirects.{column:<12} FOUND")
        else:
            print(f"  redirects.{column:<12} MISSING")

    if missing_redirect_columns:
        raise RuntimeError(
            "Required redirect column(s) missing: "
            + ", ".join(sorted(missing_redirect_columns))
        )

    # --------------------------------------------------------
    # LOAD PLAYERS
    # --------------------------------------------------------

    print_section("LOADING PLAYER MASTER")

    players = con.execute(
        """
        SELECT
            reep_id,
            label,
            status
        FROM players
        """
    ).fetchall()

    total_players = len(players)

    print(f"Total REEP players: {total_players:,}")

    player_map = {}

    for reep_id, label, status in players:
        rid = normalize_id(reep_id)

        player_map[rid] = {
            "label": label,
            "status": status,
        }

    # --------------------------------------------------------
    # STATUS DISTRIBUTION
    # --------------------------------------------------------

    print_section("PLAYER STATUS DISTRIBUTION")

    status_counts = {}

    for player in player_map.values():
        status = player["status"]

        if status is None:
            status_key = "NULL"
        else:
            status_key = str(status)

        status_counts[status_key] = (
            status_counts.get(status_key, 0) + 1
        )

    for status in sorted(status_counts):
        print(
            f"  {status:<15} "
            f"{status_counts[status]:>10,}"
        )

    # --------------------------------------------------------
    # LOAD REDIRECTS
    # --------------------------------------------------------

    print_section("LOADING REDIRECT RECORDS")

    redirect_rows = con.execute(
        """
        SELECT
            from_id,
            to_id,
            reason
        FROM redirects
        """
    ).fetchall()

    print(
        f"Total redirect rows: {len(redirect_rows):,}"
    )

    # --------------------------------------------------------
    # BUILD REDIRECT MAPS
    # --------------------------------------------------------

    source_map = {}
    target_map = {}

    self_redirects = []

    for from_id, to_id, reason in redirect_rows:

        source = normalize_id(from_id)
        target = normalize_id(to_id)

        if source is None:
            continue

        source_map.setdefault(source, []).append(
            {
                "target": target,
                "reason": reason,
            }
        )

        if target is not None:
            target_map.setdefault(target, []).append(
                {
                    "source": source,
                    "reason": reason,
                }
            )

        if source == target and source is not None:
            self_redirects.append(source)

    # --------------------------------------------------------
    # REDIRECT SOURCE/TARGET COVERAGE
    # --------------------------------------------------------

    print_section("REDIRECT SOURCE / TARGET COVERAGE")

    unique_sources = set(source_map.keys())
    unique_targets = set(target_map.keys())

    player_sources = unique_sources & set(player_map.keys())
    player_targets = unique_targets & set(player_map.keys())

    missing_sources = unique_sources - set(player_map.keys())
    missing_targets = unique_targets - set(player_map.keys())

    print(
        f"Unique redirect sources:              "
        f"{len(unique_sources):,}"
    )

    print(
        f"Unique redirect targets:              "
        f"{len(unique_targets):,}"
    )

    print(
        f"Sources found in player master:       "
        f"{len(player_sources):,}"
    )

    print(
        f"Sources missing from player master:   "
        f"{len(missing_sources):,}"
    )

    print(
        f"Targets found in player master:       "
        f"{len(player_targets):,}"
    )

    print(
        f"Targets missing from player master:   "
        f"{len(missing_targets):,}"
    )

    # --------------------------------------------------------
    # STATUS VS REDIRECT CONSISTENCY
    # --------------------------------------------------------

    print_section("STATUS VS REDIRECT CONSISTENCY")

    redirected_with_source = []
    redirected_without_source = []

    non_redirected_with_source = []

    active_with_source = []
    retired_with_source = []
    null_status_with_source = []

    for reep_id, player in player_map.items():

        status = player["status"]

        has_source = reep_id in source_map

        if status == "redirected":
            if has_source:
                redirected_with_source.append(reep_id)
            else:
                redirected_without_source.append(reep_id)

        else:
            if has_source:
                non_redirected_with_source.append(reep_id)

                if status == "active":
                    active_with_source.append(reep_id)

                elif status == "retired":
                    retired_with_source.append(reep_id)

                elif status is None:
                    null_status_with_source.append(reep_id)

    print(
        f"Redirected players with source:       "
        f"{len(redirected_with_source):,}"
    )

    print(
        f"Redirected players without source:    "
        f"{len(redirected_without_source):,}"
    )

    print(
        f"Non-redirected players with source:   "
        f"{len(non_redirected_with_source):,}"
    )

    print(
        f"Active players with redirect source:  "
        f"{len(active_with_source):,}"
    )

    print(
        f"Retired players with redirect source: "
        f"{len(retired_with_source):,}"
    )

    print(
        f"NULL-status players with source:      "
        f"{len(null_status_with_source):,}"
    )

    # --------------------------------------------------------
    # TARGET STATUS
    # --------------------------------------------------------

    print_section("REDIRECT TARGET STATUS")

    target_status_counts = {
        "active": 0,
        "retired": 0,
        "redirected": 0,
        "NULL": 0,
        "missing_from_player_master": 0,
    }

    targets_with_multiple_sources = 0
    max_sources_per_target = 0

    for target, source_records in target_map.items():

        source_count = len(source_records)

        if source_count > 1:
            targets_with_multiple_sources += 1

        max_sources_per_target = max(
            max_sources_per_target,
            source_count
        )

        if target not in player_map:
            target_status_counts[
                "missing_from_player_master"
            ] += 1
            continue

        status = player_map[target]["status"]

        if status is None:
            target_status_counts["NULL"] += 1
        elif status in target_status_counts:
            target_status_counts[status] += 1

    for status in [
        "active",
        "retired",
        "redirected",
        "NULL",
        "missing_from_player_master",
    ]:
        print(
            f"  {status:<28} "
            f"{target_status_counts[status]:>10,}"
        )

    print()
    print(
        f"Targets with multiple sources: "
        f"{targets_with_multiple_sources:,}"
    )

    print(
        f"Maximum sources per target:    "
        f"{max_sources_per_target:,}"
    )

    # --------------------------------------------------------
    # REDIRECT CHAINS
    # --------------------------------------------------------

    print_section("REDIRECT CHAINS AND CYCLES")

    redirect_graph = {}

    for source, records in source_map.items():

        targets = [
            record["target"]
            for record in records
            if record["target"] is not None
        ]

        if targets:
            redirect_graph[source] = targets

    chain_sources = []
    cycle_nodes = set()

    for start in redirect_graph:

        visited = set()
        current = start

        while current in redirect_graph:

            if current in visited:
                cycle_nodes.update(visited)
                break

            visited.add(current)

            targets = redirect_graph[current]

            if not targets:
                break

            # REEP should normally have one target.
            current = targets[0]

            if current == start:
                cycle_nodes.update(visited)
                break

        if len(visited) > 1 and not cycle_nodes.intersection(
            visited
        ):
            chain_sources.append(start)

    print(
        f"Redirect chain sources detected: "
        f"{len(chain_sources):,}"
    )

    print(
        f"Cycle nodes detected:             "
        f"{len(cycle_nodes):,}"
    )

    print(
        f"Self redirects detected:          "
        f"{len(self_redirects):,}"
    )

    # --------------------------------------------------------
    # PLAYER STATUS PROFILES
    # --------------------------------------------------------

    print_section("PLAYER STATUS PROFILES")

    profile_counts = {}

    player_records = []

    for reep_id, player in player_map.items():

        label = player["label"]
        status = player["status"]

        source_records = source_map.get(
            reep_id,
            []
        )

        target_records = target_map.get(
            reep_id,
            []
        )

        has_source = len(source_records) > 0
        has_target = len(target_records) > 0

        source_count = len(source_records)
        target_count = len(target_records)

        source_in_master = (
            source_count > 0
        )

        target_in_master = (
            target_count > 0
        )

        # Determine profile.

        if status == "redirected" and has_source:
            profile = "redirected_with_source"

        elif status == "redirected" and not has_source:
            profile = "redirected_without_source"

        elif status == "active" and has_source:
            profile = "active_with_redirect_source"

        elif status == "retired" and has_source:
            profile = "retired_with_redirect_source"

        elif status is None and has_source:
            profile = "null_status_with_redirect_source"

        elif has_target:
            profile = "redirect_target"

        elif status == "active":
            profile = "active_no_redirect_source"

        elif status == "retired":
            profile = "retired_no_redirect_source"

        elif status is None:
            profile = "null_status_no_redirect_source"

        else:
            profile = "other"

        profile_counts[profile] = (
            profile_counts.get(profile, 0) + 1
        )

        target_ids = [
            record["source"]
            for record in target_records
        ]

        target_ids_text = "|".join(
            sorted(
                set(
                    x for x in target_ids
                    if x is not None
                )
            )
        )

        source_ids = [
            record["target"]
            for record in source_records
        ]

        source_ids_text = "|".join(
            sorted(
                set(
                    x for x in source_ids
                    if x is not None
                )
            )
        )

        player_records.append(
            {
                "reep_id": reep_id,
                "label": label,
                "status": status,
                "has_redirect_source": has_source,
                "redirect_source_count": source_count,
                "has_redirect_target": has_target,
                "redirect_target_count": target_count,
                "redirect_targets": source_ids_text,
                "redirect_sources": target_ids_text,
                "status_consistency": (
                    "consistent"
                    if (
                        (status == "redirected" and has_source)
                        or
                        (status != "redirected" and not has_source)
                    )
                    else "inconsistent"
                ),
                "profile": profile,
            }
        )

    for profile in sorted(profile_counts):
        print(
            f"  {profile:<38} "
            f"{profile_counts[profile]:>10,}"
        )

    # --------------------------------------------------------
    # STATUS CONSISTENCY TOTAL
    # --------------------------------------------------------

    consistent_players = sum(
        1
        for record in player_records
        if record["status_consistency"] == "consistent"
    )

    inconsistent_players = (
        total_players - consistent_players
    )

    print_section("OVERALL STATUS CONSISTENCY")

    print(
        f"Consistent players:   {consistent_players:,}"
    )

    print(
        f"Inconsistent players: {inconsistent_players:,}"
    )

    consistency_pct = (
        (consistent_players / total_players) * 100
        if total_players
        else 0
    )

    print(
        f"Consistency coverage: {consistency_pct:.2f}%"
    )

    # --------------------------------------------------------
    # WRITE CSV
    # --------------------------------------------------------

    print_section("WRITING PLAYER-LEVEL CSV")

    import csv

    fieldnames = [
        "reep_id",
        "label",
        "status",
        "has_redirect_source",
        "redirect_source_count",
        "has_redirect_target",
        "redirect_target_count",
        "redirect_targets",
        "redirect_sources",
        "status_consistency",
        "profile",
    ]

    with open(
        CSV_PATH,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for record in sorted(
            player_records,
            key=lambda x: (
                str(x["status"]),
                str(x["reep_id"])
            )
        ):
            writer.writerow(record)

    print(f"CSV saved:")
    print(CSV_PATH)

    # --------------------------------------------------------
    # JSON SUMMARY
    # --------------------------------------------------------

    print_section("WRITING JSON SUMMARY")

    summary = {
        "audit": "reep_player_status_identity",
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "source_database": DB_PATH,

        "total_players": total_players,

        "status_distribution": status_counts,

        "redirects": {
            "total_rows": len(redirect_rows),
            "unique_sources": len(unique_sources),
            "unique_targets": len(unique_targets),
            "sources_in_player_master": len(player_sources),
            "sources_missing_from_player_master": len(
                missing_sources
            ),
            "targets_in_player_master": len(player_targets),
            "targets_missing_from_player_master": len(
                missing_targets
            ),
            "self_redirects": len(self_redirects),
            "chain_sources": len(chain_sources),
            "cycle_nodes": len(cycle_nodes),
            "targets_with_multiple_sources":
                targets_with_multiple_sources,
            "max_sources_per_target":
                max_sources_per_target,
        },

        "status_consistency": {
            "redirected_with_source":
                len(redirected_with_source),

            "redirected_without_source":
                len(redirected_without_source),

            "non_redirected_with_source":
                len(non_redirected_with_source),

            "active_with_redirect_source":
                len(active_with_source),

            "retired_with_redirect_source":
                len(retired_with_source),

            "null_status_with_redirect_source":
                len(null_status_with_source),

            "consistent_players":
                consistent_players,

            "inconsistent_players":
                inconsistent_players,

            "consistency_percentage":
                round(consistency_pct, 2),
        },

        "target_status_distribution":
            target_status_counts,

        "profile_distribution":
            profile_counts,

        "outputs": {
            "csv": CSV_PATH,
            "json": JSON_PATH,
        },
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

    print("JSON saved:")
    print(JSON_PATH)

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print_section("AUDIT COMPLETE")

    print("Source database was NOT modified.")
    print()
    print("Generated files:")
    print(f"  {CSV_PATH}")
    print(f"  {JSON_PATH}")

    con.close()


if __name__ == "__main__":
    main()