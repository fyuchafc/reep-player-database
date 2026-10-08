#!/usr/bin/env python3
"""
FYUCHA FC — REEP Player Profile Feed Exporter

Reads the audited REEP V1.2 player master and creates a compact JSONL feed
for the future WordPress player-profile importer.

One line = one canonical REEP player.

The feed intentionally does NOT include the full alias/external-ID tables.
Those remain in REEP and can be exposed through the API later.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import duckdb


SCHEMA_VERSION = "REEP V1.2"
PROFILE_FEED_VERSION = "1.0"


def clean(value):
    if value is None:
        return None
    return str(value)


def build_parser():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--database",
        default="output/reep-player-master-v1.2.duckdb",
        help="Path to the audited REEP player master database.",
    )
    p.add_argument(
        "--output",
        default="output/reep-player-profile-feed-v1.0.jsonl",
        help="Output JSONL feed path.",
    )
    return p


def main():
    args = build_parser().parse_args()

    db_path = Path(args.database)
    output_path = Path(args.output)

    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path), read_only=True)

    # Basic safety check: this exporter expects the audited V1.2 schema.
    required = {
        "players",
        "player_search",
        "player_club_evidence",
        "player_position",
        "database_metadata",
    }
    existing = {
        row[0]
        for row in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
    }
    missing = sorted(required - existing)
    if missing:
        raise SystemExit("Missing required tables: " + ", ".join(missing))

    total = con.execute("SELECT COUNT(*) FROM players").fetchone()[0]

    query = """
        SELECT
            p.reep_id,
            p.status,
            p.label,
            p.gender,
            p.country,

            pos.primary_position,
            pos.secondary_positions,
            pos.position_status,
            pos.evidence_count AS position_evidence_count,
            pos.provider_count AS position_provider_count,

            ce.entity_type AS club_entity_type,
            ce.observed_clubs,
            ce.first_observed_season,
            ce.last_observed_season,
            ce.basis,

            ps.alias_count,
            ps.external_id_count
        FROM players p
        LEFT JOIN player_position pos
            ON pos.reep_id = p.reep_id
        LEFT JOIN player_club_evidence ce
            ON ce.reep_id = p.reep_id
        LEFT JOIN player_search ps
            ON ps.reep_id = p.reep_id
        ORDER BY p.reep_id
    """

    generated_at = datetime.now(timezone.utc).isoformat()

    print("=" * 72)
    print("FYUCHA FC — REEP PLAYER PROFILE FEED EXPORT")
    print("=" * 72)
    print(f"Database: {db_path}")
    print(f"Output:   {output_path}")
    print(f"Players:  {total:,}")
    print(f"Schema:   {SCHEMA_VERSION}")
    print()

    written = 0

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        for row in con.execute(query).fetchall():
            (
                reep_id,
                status,
                label,
                gender,
                country,
                primary_position,
                secondary_positions,
                position_status,
                position_evidence_count,
                position_provider_count,
                club_entity_type,
                observed_clubs,
                first_observed_season,
                last_observed_season,
                club_basis,
                alias_count,
                external_id_count,
            ) = row

            record = {
                "profile_feed_version": PROFILE_FEED_VERSION,
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "reep_id": clean(reep_id),
                "status": clean(status),
                "label": clean(label),
                "gender": clean(gender),
                "country": clean(country),
                "position": {
                    "primary": clean(primary_position),
                    "secondary": clean(secondary_positions),
                    "status": clean(position_status),
                    "evidence_count": position_evidence_count or 0,
                    "provider_count": position_provider_count or 0,
                },
                "club_evidence": {
                    "entity_type": clean(club_entity_type),
                    "observed_clubs": clean(observed_clubs),
                    "first_observed_season": clean(first_observed_season),
                    "last_observed_season": clean(last_observed_season),
                    "basis": clean(club_basis),
                },
                "index": {
                    "alias_count": alias_count or 0,
                    "external_id_count": external_id_count or 0,
                },
            }

            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            written += 1

            if written % 10000 == 0:
                print(f"Exported: {written:,}/{total:,}")

    con.close()

    print()
    print("=" * 72)
    print("EXPORT COMPLETE")
    print("=" * 72)
    print(f"Records written: {written:,}")
    print(f"Expected players: {total:,}")
    print(f"Output: {output_path}")
    print(f"Status: {'PASS' if written == total else 'FAIL'}")


if __name__ == "__main__":
    main()
