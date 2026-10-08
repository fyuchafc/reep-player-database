#!/usr/bin/env python3
"""
FYUCHA FC — WordPress Player Profile Importer

Safe batch importer for the REEP player profile feed.

Default mode is DRY RUN. Nothing is sent to WordPress unless --execute
is explicitly supplied.

The importer uses reep_id as the permanent identity key.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


DEFAULT_FEED = "output/reep-player-profile-feed-v1.0.jsonl"


def parser():
    p = argparse.ArgumentParser()
    p.add_argument("--feed", default=DEFAULT_FEED)
    p.add_argument("--wordpress-url", required=True,
                   help="Base WordPress URL, e.g. https://example.com")
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--execute", action="store_true",
                   help="Actually create/update WordPress profiles.")
    p.add_argument("--username", help="WordPress username for Application Password auth.")
    p.add_argument("--application-password", help="WordPress Application Password.")
    return p


def slugify_fallback(label):
    import re
    value = (label or "").lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "player"


def auth_headers(args):
    if not args.username or not args.application_password:
        raise SystemExit("--execute requires --username and --application-password")
    import base64
    token = base64.b64encode(
        f"{args.username}:{args.application_password}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def request_json(url, method="GET", payload=None, headers=None):
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    req = Request(
        url,
        data=body,
        method=method,
        headers=headers or {"Accept": "application/json"},
    )

    try:
        with urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {"error": raw}
        return exc.code, data
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def make_post_payload(record):
    reep_id = record["reep_id"]
    label = record["label"] or f"Player {reep_id}"

    # Keep the first importer intentionally conservative.
    # Structured REEP data is stored in post meta; human/editorial content
    # remains available for later profile templates.
    meta = {
        "_fyucha_reep_id": reep_id,
        "_fyucha_profile_feed_version": record["profile_feed_version"],
        "_fyucha_reep_schema_version": record["schema_version"],
        "_fyucha_status": record["status"] or "",
        "_fyucha_gender": record["gender"] or "",
        "_fyucha_country": record["country"] or "",
        "_fyucha_primary_position": record["position"]["primary"] or "",
        "_fyucha_secondary_positions": record["position"]["secondary"] or "",
        "_fyucha_position_status": record["position"]["status"] or "",
        "_fyucha_position_evidence_count": record["position"]["evidence_count"],
        "_fyucha_position_provider_count": record["position"]["provider_count"],
        "_fyucha_club_evidence": json.dumps(
            record["club_evidence"], ensure_ascii=False
        ),
        "_fyucha_alias_count": record["index"]["alias_count"],
        "_fyucha_external_id_count": record["index"]["external_id_count"],
    }

    return {
        "title": label,
        "status": "publish",
        "meta": meta,
    }


def find_existing(base, reep_id, headers):
    endpoint = urljoin(base.rstrip("/") + "/", "wp-json/wp/v2/fyucha_player")
    url = endpoint + "?per_page=1&meta_key=_fyucha_reep_id&meta_value=" + reep_id
    status, data = request_json(url, headers=headers)
    if status != 200:
        raise RuntimeError(f"Lookup failed ({status}): {data}")
    return data[0] if data else None


def main():
    args = parser().parse_args()

    feed = Path(args.feed)
    if not feed.exists():
        raise SystemExit(f"Feed not found: {feed}")

    if args.batch_size < 1 or args.batch_size > 1000:
        raise SystemExit("--batch-size must be between 1 and 1000")

    base = args.wordpress_url.rstrip("/") + "/"
    headers = auth_headers(args) if args.execute else {"Accept": "application/json"}

    selected = []
    with feed.open("r", encoding="utf-8") as f:
        for index, line in enumerate(f):
            if index < args.offset:
                continue
            if len(selected) >= args.batch_size:
                break
            if line.strip():
                selected.append(json.loads(line))

    if not selected:
        print("No records selected.")
        return

    print("=" * 72)
    print("FYUCHA FC — WORDPRESS PLAYER PROFILE IMPORTER")
    print("=" * 72)
    print(f"Feed:       {feed}")
    print(f"Offset:     {args.offset:,}")
    print(f"Batch size: {len(selected):,}")
    print(f"Mode:       {'EXECUTE' if args.execute else 'DRY RUN'}")
    print()

    created = updated = skipped = 0

    for record in selected:
        reep_id = record.get("reep_id")
        label = record.get("label") or f"Player {reep_id}"

        if not reep_id:
            print("SKIP  missing REEP ID")
            skipped += 1
            continue

        payload = make_post_payload(record)

        if not args.execute:
            print(
                f"DRY RUN  {label} | REEP {reep_id} | "
                f"{record['position']['primary'] or 'position unknown'} | "
                f"{record['country'] or 'country unknown'}"
            )
            continue

        existing = find_existing(base, reep_id, headers)
        if existing:
            post_id = existing["id"]
            endpoint = urljoin(
                base, f"wp-json/wp/v2/fyucha_player/{post_id}"
            )
            status, data = request_json(
                endpoint, method="POST", payload=payload, headers=headers
            )
            if status not in (200, 201):
                raise RuntimeError(f"Update failed for {reep_id}: {status} {data}")
            print(f"UPDATE {label} | REEP {reep_id} | WP {post_id}")
            updated += 1
        else:
            endpoint = urljoin(base, "wp-json/wp/v2/fyucha_player")
            status, data = request_json(
                endpoint, method="POST", payload=payload, headers=headers
            )
            if status not in (200, 201):
                raise RuntimeError(f"Create failed for {reep_id}: {status} {data}")
            print(
                f"CREATE {label} | REEP {reep_id} | WP {data.get('id')}"
            )
            created += 1

    print()
    print("=" * 72)
    print("IMPORT SUMMARY")
    print("=" * 72)
    print(f"Selected: {len(selected):,}")
    print(f"Created:  {created:,}")
    print(f"Updated:  {updated:,}")
    print(f"Skipped:  {skipped:,}")
    print(f"Status:   {'PASS' if skipped == 0 else 'REVIEW'}")


if __name__ == "__main__":
    main()
