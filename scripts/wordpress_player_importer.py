#!/usr/bin/env python3
r"""
FYUCHA FC — Production WordPress Player Profile Importer
Production-safe importer for the REEP player profile feed.

Permanent identity:
    reep_id

Architecture:

    REEP profile feed
            |
            v
    WordPress player post
            |
            v
    Fyucha metadata sync endpoint
            |
            v
    _fyucha_* metadata

Important:

    A player is only considered successfully imported after BOTH:

        1. WordPress CREATE/UPDATE succeeds
        2. Fyucha metadata synchronization succeeds

The importer is restart-safe.

If an error occurs:

    - progress is saved
    - the failed record is NOT marked complete
    - the next run can resume from that exact record

Default mode:
    DRY RUN

Production mode:
    --execute

Example:

    python scripts\wordpress_player_importer.py ^
        --feed output\reep-player-profile-feed-v1.0.jsonl ^
        --wordpress-url https://example.com ^
        --batch-size 100 ^
        --execute ^
        --username USERNAME ^
        --application-password "APPLICATION PASSWORD"

Resume:

    python scripts\wordpress_player_importer.py ^
        --feed output\reep-player-profile-feed-v1.0.jsonl ^
        --wordpress-url https://example.com ^
        --batch-size 100 ^
        --resume ^
        --execute ^
        --username USERNAME ^
        --application-password "APPLICATION PASSWORD"
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import time

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ================================================================
# DEFAULTS
# ================================================================

DEFAULT_FEED = (
    "output/reep-player-profile-feed-v1.0.jsonl"
)

DEFAULT_STATE = (
    "output/wordpress-player-import-state.json"
)

DEFAULT_LOG = (
    "output/wordpress-player-import-log.jsonl"
)

DEFAULT_RETRIES = 3

DEFAULT_RETRY_DELAY = 3


# ================================================================
# ARGUMENTS
# ================================================================

def parser():

    p = argparse.ArgumentParser(
        description=(
            "FYUCHA FC production REEP → WordPress "
            "player profile importer."
        )
    )

    p.add_argument(
        "--feed",
        default=DEFAULT_FEED
    )

    p.add_argument(
        "--wordpress-url",
        required=True,
        help="Base WordPress URL."
    )

    p.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to process."
    )

    p.add_argument(
        "--offset",
        type=int,
        default=None,
        help=(
            "Start at a specific zero-based feed offset. "
            "Overrides saved state."
        )
    )

    p.add_argument(
        "--resume",
        action="store_true",
        help="Resume from saved importer state."
    )

    p.add_argument(
        "--state-file",
        default=DEFAULT_STATE
    )

    p.add_argument(
        "--log-file",
        default=DEFAULT_LOG
    )

    p.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="Network retries."
    )

    p.add_argument(
        "--retry-delay",
        type=int,
        default=DEFAULT_RETRY_DELAY,
        help="Seconds between retries."
    )

    p.add_argument(
        "--execute",
        action="store_true",
        help="Actually create/update WordPress profiles."
    )

    p.add_argument(
        "--username",
        help="WordPress username for Application Password auth."
    )

    p.add_argument(
        "--application-password",
        help="WordPress Application Password."
    )

    return p


# ================================================================
# TIME
# ================================================================

def utc_now():

    return datetime.now(
        timezone.utc
    ).isoformat()


# ================================================================
# AUTHENTICATION
# ================================================================

def auth_headers(args):

    args.username = args.username or os.environ.get("FYUCHA_WP_USERNAME")
    args.application_password = args.application_password or os.environ.get("FYUCHA_WP_APP_PASSWORD")

    if (
        not args.username
        or not args.application_password
    ):

        raise SystemExit(
            "--execute requires --username "
            "and --application-password"
        )

    token = base64.b64encode(
        (
            f"{args.username}:"
            f"{args.application_password}"
        ).encode()
    ).decode()

    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ================================================================
# FEED FINGERPRINT
# ================================================================

def fingerprint_feed(feed):

    sha256 = hashlib.sha256()

    with feed.open(
        "rb"
    ) as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            sha256.update(
                chunk
            )

    return sha256.hexdigest()


# ================================================================
# HTTP
# ================================================================

def request_json(
    url,
    method="GET",
    payload=None,
    headers=None,
    retries=3,
    retry_delay=3
):

    body = None

    if payload is not None:

        body = json.dumps(
            payload,
            ensure_ascii=False
        ).encode("utf-8")

    request_headers = headers or {
        "Accept": "application/json"
    }

    last_error = None

    for attempt in range(
        1,
        retries + 2
    ):

        req = Request(
            url,
            data=body,
            method=method,
            headers=request_headers,
        )

        try:

            with urlopen(
                req,
                timeout=60
            ) as response:

                raw = response.read().decode(
                    "utf-8"
                )

                return (
                    response.status,
                    json.loads(raw)
                    if raw
                    else {}
                )

        except HTTPError as exc:

            raw = exc.read().decode(
                "utf-8",
                errors="replace"
            )

            try:

                data = json.loads(raw)

            except json.JSONDecodeError:

                data = {
                    "error": raw
                }

            # ----------------------------------------------------
            # Retry temporary server errors.
            # ----------------------------------------------------

            if (
                exc.code in (
                    408,
                    429,
                    500,
                    502,
                    503,
                    504,
                )
                and attempt <= retries
            ):

                print(
                    f"  HTTP {exc.code} "
                    f"— retry {attempt}/{retries} "
                    f"in {retry_delay}s..."
                )

                time.sleep(
                    retry_delay
                )

                continue

            return (
                exc.code,
                data
            )

        except URLError as exc:

            last_error = exc

            if attempt <= retries:

                print(
                    f"  Network error "
                    f"— retry {attempt}/{retries} "
                    f"in {retry_delay}s..."
                )

                time.sleep(
                    retry_delay
                )

                continue

            raise RuntimeError(
                f"Network error after "
                f"{retries} retries: {exc}"
            ) from exc

    raise RuntimeError(
        f"Request failed: {last_error}"
    )


# ================================================================
# PAYLOADS
# ================================================================

def make_post_payload(record):

    reep_id = record[
        "reep_id"
    ]

    label = (
        record.get("label")
        or f"Player {reep_id}"
    )

    return {
        "title": label,
        "status": "publish",
    }


def make_sync_payload(record):

    position = (
        record.get("position")
        or {}
    )

    index = (
        record.get("index")
        or {}
    )

    return {

        "reep_id":
            record["reep_id"],

        "profile_feed_version":
            record.get(
                "profile_feed_version"
            ),

        "schema_version":
            record.get(
                "schema_version"
            ),

        "status":
            record.get(
                "status"
            ) or "",

        "gender":
            record.get(
                "gender"
            ) or "",

        "country":
            record.get(
                "country"
            ) or "",

        "primary_position":
            position.get(
                "primary"
            ) or "",

        "secondary_positions":
            position.get(
                "secondary"
            ) or "",

        "position_status":
            position.get(
                "status"
            ) or "",

        "position_evidence_count":
            position.get(
                "evidence_count"
            ),

        "position_provider_count":
            position.get(
                "provider_count"
            ),

        "club_evidence":
            record.get(
                "club_evidence"
            ),

        "alias_count":
            index.get(
                "alias_count"
            ),

        "external_id_count":
            index.get(
                "external_id_count"
            ),
    }


# ================================================================
# EXISTING PLAYER LOOKUP
# ================================================================

def find_existing(
    base,
    reep_id,
    headers,
    args
):

    endpoint = urljoin(
        base,
        "wp-json/fyucha/v1/player/"
    )

    url = endpoint + quote(
        reep_id,
        safe=""
    )

    status, data = request_json(
        url,
        headers=headers,
        retries=args.retries,
        retry_delay=args.retry_delay
    )

    if status == 200:

        if not data.get("id"):

            raise RuntimeError(
                f"Invalid lookup response "
                f"for {reep_id}: {data}"
            )

        returned_reep_id = data.get(
            "reep_id"
        )

        if returned_reep_id != reep_id:

            raise RuntimeError(
                "IDENTITY SAFETY CHECK FAILED: "
                f"requested {reep_id}, "
                f"WordPress returned "
                f"{returned_reep_id}"
            )

        return data

    if status == 404:

        return None

    raise RuntimeError(
        f"Lookup failed for {reep_id}: "
        f"{status} {data}"
    )


# ================================================================
# METADATA SYNCHRONIZATION
# ================================================================

def sync_metadata(
    base,
    post_id,
    record,
    headers,
    args
):

    endpoint = urljoin(
        base,
        (
            f"wp-json/fyucha/v1/player/"
            f"{post_id}/sync"
        )
    )

    payload = make_sync_payload(
        record
    )

    status, data = request_json(
        endpoint,
        method="POST",
        payload=payload,
        headers=headers,
        retries=args.retries,
        retry_delay=args.retry_delay
    )

    if status not in (
        200,
        201
    ):

        raise RuntimeError(
            f"Metadata sync failed for "
            f"{record['reep_id']}: "
            f"{status} {data}"
        )

    returned_reep_id = data.get(
        "reep_id"
    )

    if returned_reep_id != record[
        "reep_id"
    ]:

        raise RuntimeError(
            "IDENTITY SAFETY CHECK FAILED "
            "DURING METADATA SYNC: "
            f"requested "
            f"{record['reep_id']}, "
            f"WordPress returned "
            f"{returned_reep_id}"
        )

    return data


# ================================================================
# STATE
# ================================================================

def default_state(
    feed,
    feed_hash
):

    return {

        "state_version": "1.0",

        "feed": str(
            feed
        ),

        "feed_sha256":
            feed_hash,

        "next_offset": 0,

        "selected": 0,

        "created": 0,

        "updated": 0,

        "failed": 0,

        "started_at":
            None,

        "last_success_at":
            None,

        "completed_at":
            None,

        "status":
            "NOT_STARTED",
    }


def save_state(
    state_path,
    state
):

    state_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_path = state_path.with_suffix(
        ".tmp"
    )

    with temp_path.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            state,
            f,
            indent=2,
            ensure_ascii=False
        )

    temp_path.replace(
        state_path
    )


def load_state(
    state_path
):

    if not state_path.exists():

        return None

    with state_path.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ================================================================
# LOGGING
# ================================================================

def write_log(
    log_path,
    event
):

    log_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    event = {
        "timestamp":
            utc_now(),
        **event,
    }

    with log_path.open(
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(
                event,
                ensure_ascii=False
            )
            + "\n"
        )


# ================================================================
# LOAD BATCH
# ================================================================

def load_selected(
    feed,
    offset,
    batch_size
):

    selected = []

    with feed.open(
        "r",
        encoding="utf-8"
    ) as f:

        for index, line in enumerate(
            f
        ):

            if index < offset:
                continue

            if len(selected) >= batch_size:
                break

            if line.strip():

                selected.append(
                    (
                        index,
                        json.loads(line)
                    )
                )

    return selected


# ================================================================
# PROCESS ONE RECORD
# ================================================================

def process_record(
    record,
    base,
    headers,
    args
):

    reep_id = record.get(
        "reep_id"
    )

    label = (
        record.get("label")
        or f"Player {reep_id}"
    )

    if not reep_id:

        raise RuntimeError(
            "Missing REEP ID."
        )

    post_payload = make_post_payload(
        record
    )

    existing = find_existing(
        base,
        reep_id,
        headers,
        args
    )

    # ============================================================
    # UPDATE
    # ============================================================

    if existing:

        post_id = existing[
            "id"
        ]

        endpoint = urljoin(
            base,
            (
                f"wp-json/wp/v2/"
                f"fyucha_player/{post_id}"
            )
        )

        status, data = request_json(
            endpoint,
            method="POST",
            payload=post_payload,
            headers=headers,
            retries=args.retries,
            retry_delay=args.retry_delay
        )

        if status not in (
            200,
            201
        ):

            raise RuntimeError(
                f"Update failed for "
                f"{reep_id}: "
                f"{status} {data}"
            )

        sync_metadata(
            base,
            post_id,
            record,
            headers,
            args
        )

        return {
            "action": "UPDATE",
            "reep_id": reep_id,
            "label": label,
            "post_id": post_id,
        }

    # ============================================================
    # CREATE
    # ============================================================

    endpoint = urljoin(
        base,
        "wp-json/wp/v2/fyucha_player"
    )

    status, data = request_json(
        endpoint,
        method="POST",
        payload=post_payload,
        headers=headers,
        retries=args.retries,
        retry_delay=args.retry_delay
    )

    if status not in (
        200,
        201
    ):

        raise RuntimeError(
            f"Create failed for "
            f"{reep_id}: "
            f"{status} {data}"
        )

    created_id = data.get(
        "id"
    )

    if not created_id:

        raise RuntimeError(
            f"WordPress created "
            f"{reep_id} but returned "
            f"no post ID."
        )

    sync_metadata(
        base,
        created_id,
        record,
        headers,
        args
    )

    return {
        "action": "CREATE",
        "reep_id": reep_id,
        "label": label,
        "post_id": created_id,
    }


# ================================================================
# MAIN
# ================================================================

def main():

    args = parser().parse_args()

    feed = Path(
        args.feed
    )

    state_path = Path(
        args.state_file
    )

    log_path = Path(
        args.log_file
    )

    if not feed.exists():

        raise SystemExit(
            f"Feed not found: {feed}"
        )

    if (
        args.batch_size < 1
        or args.batch_size > 1000
    ):

        raise SystemExit(
            "--batch-size must be "
            "between 1 and 1000"
        )

    if args.offset is not None and (
        args.offset < 0
    ):

        raise SystemExit(
            "--offset cannot be negative"
        )

    if args.retries < 0:

        raise SystemExit(
            "--retries cannot be negative"
        )

    if args.retry_delay < 0:

        raise SystemExit(
            "--retry-delay cannot be negative"
        )

    # ============================================================
    # FEED FINGERPRINT
    # ============================================================

    print(
        "Calculating feed fingerprint..."
    )

    feed_hash = fingerprint_feed(
        feed
    )

    # ============================================================
    # STATE
    # ============================================================

    state = load_state(
        state_path
    )

    if args.resume:

        if not state:

            raise SystemExit(
                "Cannot resume: "
                "no saved state file exists."
            )

        if state.get(
            "feed_sha256"
        ) != feed_hash:

            raise SystemExit(
                "SAFETY STOP: The current "
                "feed does not match the "
                "feed recorded in the saved "
                "import state."
            )

        start_offset = state.get(
            "next_offset",
            0
        )

    elif args.offset is not None:

        start_offset = args.offset

    else:

        start_offset = 0

        state = default_state(
            feed,
            feed_hash
        )

    # ============================================================
    # CREATE NEW STATE IF NECESSARY
    # ============================================================

    if state is None:

        state = default_state(
            feed,
            feed_hash
        )

    # ============================================================
    # VERIFY STATE FEED
    # ============================================================

    if state.get(
        "feed_sha256"
    ) != feed_hash:

        raise SystemExit(
            "SAFETY STOP: Feed fingerprint "
            "does not match saved state."
        )

    state[
        "status"
    ] = "RUNNING"

    if not state.get(
        "started_at"
    ):

        state[
            "started_at"
        ] = utc_now()

    save_state(
        state_path,
        state
    )

    # ============================================================
    # AUTH
    # ============================================================

    if args.execute:

        headers = auth_headers(
            args
        )

    else:

        headers = {
            "Accept":
                "application/json"
        }

    base = (
        args.wordpress_url.rstrip("/")
        + "/"
    )

    # ============================================================
    # LOAD BATCH
    # ============================================================

    selected = load_selected(
        feed,
        start_offset,
        args.batch_size
    )

    if not selected:

        state[
            "status"
        ] = "COMPLETE"

        state[
            "completed_at"
        ] = utc_now()

        state[
            "next_offset"
        ] = start_offset

        save_state(
            state_path,
            state
        )

        print()
        print(
            "No records selected."
        )
        print(
            "The importer may already "
            "be complete."
        )

        return

    # ============================================================
    # HEADER
    # ============================================================

    print()
    print(
        "=" * 72
    )

    print(
        "FYUCHA FC — PRODUCTION "
        "WORDPRESS PLAYER IMPORTER"
    )

    print(
        "=" * 72
    )

    print(
        f"Feed:       {feed}"
    )

    print(
        f"Offset:     {start_offset:,}"
    )

    print(
        f"Batch size: {len(selected):,}"
    )

    print(
        "Mode:       "
        f"{'EXECUTE' if args.execute else 'DRY RUN'}"
    )

    print(
        f"State:      {state_path}"
    )

    print(
        f"Log:        {log_path}"
    )

    print()

    batch_created = 0
    batch_updated = 0

    # ============================================================
    # PROCESS
    # ============================================================

    for feed_index, record in selected:

        reep_id = record.get(
            "reep_id"
        )

        label = (
            record.get("label")
            or f"Player {reep_id}"
        )

        try:

            # ----------------------------------------------------
            # DRY RUN
            # ----------------------------------------------------

            if not args.execute:

                print(
                    f"DRY RUN  {label} | "
                    f"REEP {reep_id}"
                )

                state[
                    "next_offset"
                ] = feed_index + 1

                state[
                    "selected"
                ] += 1

                save_state(
                    state_path,
                    state
                )

                continue

            # ----------------------------------------------------
            # EXECUTE
            # ----------------------------------------------------

            result = process_record(
                record,
                base,
                headers,
                args
            )

            action = result[
                "action"
            ]

            post_id = result[
                "post_id"
            ]

            if action == "CREATE":

                batch_created += 1

                state[
                    "created"
                ] += 1

            elif action == "UPDATE":

                batch_updated += 1

                state[
                    "updated"
                ] += 1

            state[
                "selected"
            ] += 1

            # ----------------------------------------------------
            # IMPORTANT:
            #
            # Advance the saved offset ONLY AFTER
            # CREATE/UPDATE + metadata sync succeeds.
            # ----------------------------------------------------

            state[
                "next_offset"
            ] = feed_index + 1

            state[
                "last_success_at"
            ] = utc_now()

            save_state(
                state_path,
                state
            )

            write_log(
                log_path,
                {
                    "event":
                        "success",

                    "feed_index":
                        feed_index,

                    "reep_id":
                        reep_id,

                    "label":
                        label,

                    "action":
                        action,

                    "wordpress_post_id":
                        post_id,
                }
            )

            print(
                f"{action:<7} "
                f"{label} | "
                f"REEP {reep_id} | "
                f"WP {post_id}"
            )

        except Exception as exc:

            # ----------------------------------------------------
            # FAILURE
            #
            # Do NOT advance next_offset.
            # This makes the run restart-safe.
            # ----------------------------------------------------

            state[
                "failed"
            ] += 1

            state[
                "status"
            ] = "FAILED"

            save_state(
                state_path,
                state
            )

            write_log(
                log_path,
                {
                    "event":
                        "failure",

                    "feed_index":
                        feed_index,

                    "reep_id":
                        reep_id,

                    "label":
                        label,

                    "error":
                        str(exc),
                }
            )

            print()
            print(
                "=" * 72
            )

            print(
                "IMPORT STOPPED SAFELY"
            )

            print(
                "=" * 72
            )

            print(
                f"Failed offset: {feed_index:,}"
            )

            print(
                f"REEP ID:       {reep_id}"
            )

            print(
                f"Player:        {label}"
            )

            print(
                f"Error:         {exc}"
            )

            print()
            print(
                "Progress has been saved."
            )

            print(
                "The next run can use "
                "--resume to continue "
                "from this player."
            )

            print()

            raise SystemExit(
                1
            )

    # ============================================================
    # BATCH COMPLETE
    # ============================================================

    state[
        "status"
    ] = "READY_TO_RESUME"

    save_state(
        state_path,
        state
    )

    # ============================================================
    # SUMMARY
    # ============================================================

    print()

    print(
        "=" * 72
    )

    print(
        "IMPORT BATCH SUMMARY"
    )

    print(
        "=" * 72
    )

    print(
        f"Selected: {len(selected):,}"
    )

    print(
        f"Created:  {batch_created:,}"
    )

    print(
        f"Updated:  {batch_updated:,}"
    )

    print(
        "Skipped:  0"
    )

    print(
        f"Next offset: "
        f"{state['next_offset']:,}"
    )

    print(
        "Status:   PASS"
    )

    print()

    print(
        "Progress saved."
    )

    print(
        "Use --resume for the next batch."
    )


if __name__ == "__main__":

    main()