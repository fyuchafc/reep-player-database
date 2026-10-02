import csv
import json
import os
import sys
from collections import Counter, defaultdict

import duckdb


# ============================================================
# REEP PLAYER REDIRECT IDENTITY AUDIT
# ============================================================
#
# READ-ONLY AUDIT
#
# Purpose:
#   Audit player redirects and determine how redirected players
#   relate to:
#       - redirect targets
#       - QIDs
#       - external IDs
#       - aliases
#       - labels
#       - status
#
# This script does NOT:
#   - modify the REEP database
#   - merge players
#   - delete players
#   - modify redirects
#   - modify QIDs
#   - modify external IDs
#   - modify players.json
#
# Redirects are treated as source data.
# ============================================================


SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = "output"

JSON_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "reep-player-redirect-identity-audit.json"
)

CSV_OUTPUT = os.path.join(
    OUTPUT_DIR,
    "reep-player-redirect-identity.csv"
)


def safe(value):
    if value is None:
        return None
    return str(value)


def norm(value):
    if value is None:
        return ""
    return str(value).strip()


def main():

    print("=" * 70)
    print("REEP PLAYER REDIRECT IDENTITY AUDIT")
    print("=" * 70)
    print()
    print("READ-ONLY — source database will NOT be modified.")
    print()

    if not os.path.exists(SOURCE_DB):
        print("ERROR: Source database not found:")
        print(SOURCE_DB)
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    file_size = os.path.getsize(SOURCE_DB)

    print("SOURCE DATABASE")
    print("-" * 70)
    print(SOURCE_DB)
    print(
        f"File size: {file_size:,} bytes "
        f"({file_size / (1024 * 1024):.2f} MiB)"
    )
    print()

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
        "main.redirects",
        "main.overlay_links",
        "main.overlay_xids",
        "main.aliases",
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
    # Load all player redirects
    # --------------------------------------------------------

    print("LOADING PLAYER REDIRECTS...")
    print()

    redirect_rows = con.execute(
        """
        SELECT
            r.from_id,
            r.to_id,
            r.reason,
            fp.label AS from_label,
            fp.status AS from_status,
            fp.gender AS from_gender,
            tp.label AS to_label,
            tp.status AS to_status,
            tp.gender AS to_gender
        FROM main.redirects r
        INNER JOIN main.players fp
            ON fp.reep_id = r.from_id
        LEFT JOIN main.players tp
            ON tp.reep_id = r.to_id
        ORDER BY
            r.from_id
        """
    ).fetchall()

    print(
        f"Player redirect rows: {len(redirect_rows):,}"
    )
    print()

    # --------------------------------------------------------
    # Build redirect sets
    # --------------------------------------------------------

    redirect_from_ids = {
        row[0]
        for row in redirect_rows
    }

    redirected_targets = {
        row[1]
        for row in redirect_rows
        if row[1] is not None
    }

    target_not_published = [
        row
        for row in redirect_rows
        if row[1] is None
    ]

    # --------------------------------------------------------
    # Check redirect chains
    # --------------------------------------------------------

    redirect_map = {
        row[0]: row[1]
        for row in redirect_rows
    }

    redirect_chains = []
    self_redirects = []

    for from_id, to_id in redirect_map.items():

        if to_id is None:
            continue

        if from_id == to_id:
            self_redirects.append(
                {
                    "from_id": from_id,
                    "to_id": to_id,
                }
            )
            continue

        if to_id in redirect_map:
            redirect_chains.append(
                {
                    "from_id": from_id,
                    "to_id": to_id,
                    "target_redirects_to": redirect_map[to_id],
                }
            )

    # --------------------------------------------------------
    # Load QIDs for players
    # --------------------------------------------------------

    print("LOADING PLAYER QID LINKS...")
    print()

    qid_rows = con.execute(
        """
        SELECT
            ol.reep_id,
            ol.qid,
            ol.confidence,
            ol.dob_check,
            ol.entity_type,
            ol.inherited_count,
            ol.inherited
        FROM main.overlay_links ol
        INNER JOIN main.players p
            ON p.reep_id = ol.reep_id
        WHERE ol.qid IS NOT NULL
          AND TRIM(CAST(ol.qid AS VARCHAR)) <> ''
        """
    ).fetchall()

    qids_by_player = defaultdict(list)

    for row in qid_rows:
        qids_by_player[row[0]].append(
            {
                "qid": safe(row[1]),
                "confidence": safe(row[2]),
                "dob_check": safe(row[3]),
                "entity_type": safe(row[4]),
                "inherited_count": row[5],
                "inherited": safe(row[6]),
            }
        )

    # --------------------------------------------------------
    # Load external IDs for players
    # --------------------------------------------------------

    print("LOADING PLAYER EXTERNAL IDs...")
    print()

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
        FROM main.overlay_xids x
        INNER JOIN main.players p
            ON p.reep_id = x.reep_id
        WHERE x.external_id IS NOT NULL
          AND TRIM(CAST(x.external_id AS VARCHAR)) <> ''
        """
    ).fetchall()

    xids_by_player = defaultdict(list)

    for row in xid_rows:
        xids_by_player[row[0]].append(
            {
                "provider": safe(row[1]),
                "property": safe(row[2]),
                "external_id": safe(row[3]),
                "rank": safe(row[4]),
                "confidence": safe(row[5]),
                "dob_check": safe(row[6]),
                "qid": safe(row[7]),
            }
        )

    # --------------------------------------------------------
    # Load aliases for players
    # --------------------------------------------------------

    print("LOADING PLAYER ALIASES...")
    print()

    alias_rows = con.execute(
        """
        SELECT
            a.reep_id,
            a.alias,
            a.kind,
            a.rank,
            a.language
        FROM main.aliases a
        INNER JOIN main.players p
            ON p.reep_id = a.reep_id
        """
    ).fetchall()

    aliases_by_player = defaultdict(list)

    for row in alias_rows:
        aliases_by_player[row[0]].append(
            {
                "alias": safe(row[1]),
                "kind": safe(row[2]),
                "rank": safe(row[3]),
                "language": safe(row[4]),
            }
        )

    # --------------------------------------------------------
    # Analyze redirects
    # --------------------------------------------------------

    merged_count = 0
    target_not_published_count = 0

    redirect_details = []

    for row in redirect_rows:

        (
            from_id,
            to_id,
            reason,
            from_label,
            from_status,
            from_gender,
            to_label,
            to_status,
            to_gender,
        ) = row

        if to_id is None:
            target_not_published_count += 1
        else:
            merged_count += 1

        from_qids = qids_by_player.get(
            from_id,
            []
        )

        to_qids = qids_by_player.get(
            to_id,
            []
        ) if to_id else []

        from_xids = xids_by_player.get(
            from_id,
            []
        )

        to_xids = xids_by_player.get(
            to_id,
            []
        ) if to_id else []

        from_aliases = aliases_by_player.get(
            from_id,
            []
        )

        to_aliases = aliases_by_player.get(
            to_id,
            []
        ) if to_id else []

        from_qid_set = {
            item["qid"]
            for item in from_qids
        }

        to_qid_set = {
            item["qid"]
            for item in to_qids
        }

        shared_qids = sorted(
            from_qid_set & to_qid_set
        )

        from_external_keys = {
            (
                item["provider"],
                item["property"],
                item["external_id"],
            )
            for item in from_xids
        }

        to_external_keys = {
            (
                item["provider"],
                item["property"],
                item["external_id"],
            )
            for item in to_xids
        }

        shared_external_keys = sorted(
            from_external_keys & to_external_keys
        )

        same_label = (
            norm(from_label).lower()
            == norm(to_label).lower()
            if to_label is not None
            else False
        )

        redirect_details.append(
            {
                "from_id": from_id,
                "from_label": safe(from_label),
                "from_status": safe(from_status),
                "from_gender": safe(from_gender),

                "to_id": to_id,
                "to_label": safe(to_label),
                "to_status": safe(to_status),
                "to_gender": safe(to_gender),

                "reason": safe(reason),

                "target_published": to_id is not None,

                "same_label": same_label,

                "from_qid_count": len(from_qids),
                "to_qid_count": len(to_qids),
                "shared_qid_count": len(shared_qids),
                "shared_qids": shared_qids,

                "from_external_id_count": len(from_xids),
                "to_external_id_count": len(to_xids),
                "shared_external_id_count": len(
                    shared_external_keys
                ),

                "from_alias_count": len(from_aliases),
                "to_alias_count": len(to_aliases),

                "from_qids": from_qids,
                "to_qids": to_qids,

                "shared_external_ids": [
                    {
                        "provider": item[0],
                        "property": item[1],
                        "external_id": item[2],
                    }
                    for item in shared_external_keys
                ],
            }
        )

    # --------------------------------------------------------
    # Summary counters
    # --------------------------------------------------------

    reason_counts = Counter(
        safe(row[2])
        for row in redirect_rows
    )

    from_status_counts = Counter(
        safe(row[4])
        for row in redirect_rows
    )

    target_status_counts = Counter(
        safe(row[7])
        for row in redirect_rows
        if row[7] is not None
    )

    shared_qid_redirects = [
        detail
        for detail in redirect_details
        if detail["shared_qid_count"] > 0
    ]

    shared_external_redirects = [
        detail
        for detail in redirect_details
        if detail["shared_external_id_count"] > 0
    ]

    same_label_redirects = [
        detail
        for detail in redirect_details
        if detail["same_label"]
    ]

    different_label_redirects = [
        detail
        for detail in redirect_details
        if not detail["same_label"]
    ]

    # --------------------------------------------------------
    # Redirect target fan-in
    # --------------------------------------------------------

    target_sources = defaultdict(list)

    for row in redirect_rows:
        if row[1] is not None:
            target_sources[row[1]].append(
                row[0]
            )

    multi_source_targets = {
        target: sources
        for target, sources in target_sources.items()
        if len(sources) > 1
    }

    # --------------------------------------------------------
    # Redirects with no QID on either side
    # --------------------------------------------------------

    no_qid_either_side = [
        detail
        for detail in redirect_details
        if detail["from_qid_count"] == 0
        and detail["to_qid_count"] == 0
    ]

    # --------------------------------------------------------
    # Redirects with no external ID on either side
    # --------------------------------------------------------

    no_xid_either_side = [
        detail
        for detail in redirect_details
        if detail["from_external_id_count"] == 0
        and detail["to_external_id_count"] == 0
    ]

    # --------------------------------------------------------
    # Build audit
    # --------------------------------------------------------

    audit = {
        "audit": {
            "name": "REEP Player Redirect Identity Audit",
            "read_only": True,
            "source_database": SOURCE_DB,
            "source_file_size_bytes": file_size,
        },

        "totals": {
            "player_redirect_rows": len(redirect_rows),
            "unique_redirect_sources": len(
                redirect_from_ids
            ),
            "unique_redirect_targets": len(
                redirected_targets
            ),
            "merged_redirects": merged_count,
            "target_not_published": (
                target_not_published_count
            ),
            "redirect_chains": len(
                redirect_chains
            ),
            "self_redirects": len(
                self_redirects
            ),
            "targets_with_multiple_sources": len(
                multi_source_targets
            ),
            "redirects_with_shared_qid": len(
                shared_qid_redirects
            ),
            "redirects_with_shared_external_id": len(
                shared_external_redirects
            ),
            "same_label_redirects": len(
                same_label_redirects
            ),
            "different_label_redirects": len(
                different_label_redirects
            ),
            "redirects_without_qid_on_either_side": len(
                no_qid_either_side
            ),
            "redirects_without_external_id_on_either_side": len(
                no_xid_either_side
            ),
        },

        "reason_distribution": dict(
            reason_counts
        ),

        "source_status_distribution": dict(
            from_status_counts
        ),

        "target_status_distribution": dict(
            target_status_counts
        ),

        "multi_source_targets": [
            {
                "target_id": target,
                "source_count": len(sources),
                "source_ids": sorted(sources),
            }
            for target, sources
            in sorted(
                multi_source_targets.items()
            )
        ],

        "redirect_chains": redirect_chains,

        "self_redirects": self_redirects,

        "redirects": redirect_details,
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
                "from_id",
                "from_label",
                "from_status",
                "from_gender",
                "to_id",
                "to_label",
                "to_status",
                "to_gender",
                "reason",
                "target_published",
                "same_label",
                "from_qid_count",
                "to_qid_count",
                "shared_qid_count",
                "shared_qids",
                "from_external_id_count",
                "to_external_id_count",
                "shared_external_id_count",
                "shared_external_ids",
                "from_alias_count",
                "to_alias_count",
            ]
        )

        for detail in redirect_details:

            shared_external_ids = "|".join(
                (
                    f"{item['provider']}:"
                    f"{item['property']}:"
                    f"{item['external_id']}"
                )
                for item in detail[
                    "shared_external_ids"
                ]
            )

            writer.writerow(
                [
                    detail["from_id"],
                    detail["from_label"],
                    detail["from_status"],
                    detail["from_gender"],
                    detail["to_id"],
                    detail["to_label"],
                    detail["to_status"],
                    detail["to_gender"],
                    detail["reason"],
                    detail["target_published"],
                    detail["same_label"],
                    detail["from_qid_count"],
                    detail["to_qid_count"],
                    detail["shared_qid_count"],
                    "|".join(
                        detail["shared_qids"]
                    ),
                    detail["from_external_id_count"],
                    detail["to_external_id_count"],
                    detail["shared_external_id_count"],
                    shared_external_ids,
                    detail["from_alias_count"],
                    detail["to_alias_count"],
                ]
            )

    # --------------------------------------------------------
    # Console output
    # --------------------------------------------------------

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    print(
        f"Player redirect rows:                 "
        f"{len(redirect_rows):,}"
    )

    print(
        f"Unique redirect sources:               "
        f"{len(redirect_from_ids):,}"
    )

    print(
        f"Unique redirect targets:               "
        f"{len(redirected_targets):,}"
    )

    print(
        f"Merged redirects:                      "
        f"{merged_count:,}"
    )

    print(
        f"Target-not-published:                  "
        f"{target_not_published_count:,}"
    )

    print(
        f"Redirect chains:                       "
        f"{len(redirect_chains):,}"
    )

    print(
        f"Self redirects:                        "
        f"{len(self_redirects):,}"
    )

    print(
        f"Targets with multiple sources:         "
        f"{len(multi_source_targets):,}"
    )

    print(
        f"Redirects sharing a QID:               "
        f"{len(shared_qid_redirects):,}"
    )

    print(
        f"Redirects sharing an external ID:      "
        f"{len(shared_external_redirects):,}"
    )

    print(
        f"Same-label redirects:                  "
        f"{len(same_label_redirects):,}"
    )

    print(
        f"Different-label redirects:             "
        f"{len(different_label_redirects):,}"
    )

    print(
        f"No QID on either side:                 "
        f"{len(no_qid_either_side):,}"
    )

    print(
        f"No external ID on either side:         "
        f"{len(no_xid_either_side):,}"
    )

    print()

    print("=" * 70)
    print("REDIRECT REASON DISTRIBUTION")
    print("=" * 70)

    for reason, count in sorted(
        reason_counts.items(),
        key=lambda item: (
            -item[1],
            str(item[0])
        )
    ):
        print(
            f"{reason}: {count:,}"
        )

    print()

    print("=" * 70)
    print("TARGETS WITH MULTIPLE REDIRECT SOURCES")
    print("=" * 70)

    if not multi_source_targets:
        print(
            "No targets have multiple redirect sources."
        )
    else:
        for target, sources in sorted(
            multi_source_targets.items(),
            key=lambda item: (
                -len(item[1]),
                item[0]
            )
        )[:20]:

            target_label = con.execute(
                """
                SELECT label
                FROM main.players
                WHERE reep_id = ?
                """,
                [target]
            ).fetchone()

            label = (
                target_label[0]
                if target_label
                else None
            )

            print(
                f"{target} | "
                f"{label} | "
                f"sources={len(sources)}"
            )

            for source in sources:
                print(
                    f"    <- {source}"
                )

    print()

    print("=" * 70)
    print("REDIRECTS SHARING QIDS")
    print("=" * 70)

    if not shared_qid_redirects:
        print(
            "No redirects share a QID."
        )
    else:
        for detail in shared_qid_redirects[:20]:
            print(
                f"{detail['from_id']} "
                f"({detail['from_label']}) "
                f"-> "
                f"{detail['to_id']} "
                f"({detail['to_label']}) | "
                f"shared_qids={detail['shared_qids']}"
            )

    print()

    print("=" * 70)
    print("REDIRECTS SHARING EXTERNAL IDs")
    print("=" * 70)

    if not shared_external_redirects:
        print(
            "No redirects share an exact external ID."
        )
    else:
        for detail in shared_external_redirects[:20]:
            print(
                f"{detail['from_id']} "
                f"({detail['from_label']}) "
                f"-> "
                f"{detail['to_id']} "
                f"({detail['to_label']}) | "
                f"shared="
                f"{detail['shared_external_ids']}"
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
    print("No redirects were modified.")
    print("No QIDs were modified.")
    print("No external IDs were modified.")

    con.close()


if __name__ == "__main__":
    main()