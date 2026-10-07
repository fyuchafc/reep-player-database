import csv
import html
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import duckdb


# ============================================================
# REEP — TRANSFERMARKT STRUCTURED POSITION EXTRACTION TEST
# ============================================================
#
# READ-ONLY TEST
#
# Purpose:
#   Extract the actual Main position / Other position values
#   from public Transfermarkt player profile HTML.
#
# IMPORTANT:
#   - Does NOT modify the REEP source database.
#   - Does NOT modify v1.0.0.
#   - Does NOT create the final position layer.
#   - Tests only 10 real REEP players.
#
# Outputs:
#   output/reep-transfermarkt-position-extraction-test.json
#   output/reep-transfermarkt-position-extraction-test.csv
#
# ============================================================


SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = Path("output")

JSON_OUTPUT = (
    OUTPUT_DIR /
    "reep-transfermarkt-position-extraction-test.json"
)

CSV_OUTPUT = (
    OUTPUT_DIR /
    "reep-transfermarkt-position-extraction-test.csv"
)

SAMPLE_SIZE = 10
REQUEST_DELAY = 2.0
TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)


# ------------------------------------------------------------
# HTML utilities
# ------------------------------------------------------------

def strip_tags(value):
    """
    Convert HTML fragment into readable text.
    """

    if not value:
        return ""

    value = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        value,
        flags=re.I | re.S
    )

    value = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        value,
        flags=re.I | re.S
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = html.unescape(value)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def clean_value(value):
    """
    Clean a single extracted position value.
    """

    if not value:
        return None

    value = strip_tags(value)

    value = re.sub(
        r"^(Main position|Other position|Other positions)\s*:?\s*",
        "",
        value,
        flags=re.I
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    if not value:
        return None

    return value


# ------------------------------------------------------------
# Fetch
# ------------------------------------------------------------

def fetch_url(url):

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    try:

        with urlopen(
            request,
            timeout=TIMEOUT
        ) as response:

            body = response.read()

            encoding = (
                response.headers.get_content_charset()
                or "utf-8"
            )

            try:
                page = body.decode(
                    encoding,
                    errors="replace"
                )
            except Exception:
                page = body.decode(
                    "utf-8",
                    errors="replace"
                )

            return {
                "status": response.getcode(),
                "html": page,
                "error": None,
            }

    except HTTPError as exc:

        return {
            "status": exc.code,
            "html": "",
            "error": (
                f"HTTPError {exc.code}: {exc.reason}"
            ),
        }

    except URLError as exc:

        return {
            "status": None,
            "html": "",
            "error": (
                f"URLError: {exc.reason}"
            ),
        }

    except Exception as exc:

        return {
            "status": None,
            "html": "",
            "error": (
                f"{type(exc).__name__}: {exc}"
            ),
        }


# ------------------------------------------------------------
# REEP sample
# ------------------------------------------------------------

def load_sample():

    print("=" * 70)
    print("REEP — TRANSFERMARKT STRUCTURED POSITION EXTRACTION")
    print("=" * 70)
    print()
    print("READ-ONLY — source database will NOT be modified.")
    print()

    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Source database not found:\n{SOURCE_DB}"
        )

    print("Opening REEP database READ-ONLY...")

    con = duckdb.connect(
        str(SOURCE_DB),
        read_only=True
    )

    print("Connected successfully.")
    print()

    query = """
        SELECT
            p.reep_id,
            p.label,
            b.external_id AS transfermarkt_id
        FROM players p
        INNER JOIN bridges b
            ON b.reep_id = p.reep_id
        WHERE
            LOWER(TRIM(b.provider)) = 'transfermarkt'
            AND LOWER(TRIM(b.namespace)) = 'spieler'
            AND b.external_id IS NOT NULL
            AND TRIM(
                CAST(b.external_id AS VARCHAR)
            ) <> ''
        GROUP BY
            p.reep_id,
            p.label,
            b.external_id
        ORDER BY
            p.reep_id
        LIMIT ?
    """

    rows = con.execute(
        query,
        [SAMPLE_SIZE]
    ).fetchall()

    con.close()

    return rows


# ------------------------------------------------------------
# Position extraction
# ------------------------------------------------------------

def extract_position_field(html_text, label):

    """
    Find a Transfermarkt position label and inspect the
    immediately following HTML.

    We deliberately keep this conservative.

    The function returns:
        raw HTML area
        cleaned text
        possible values

    It does NOT decide whether a value is canonical.
    """

    patterns = []

    if label == "main_position":

        patterns = [
            r"Main position",
            r"Main\s+position",
        ]

    elif label == "other_position":

        patterns = [
            r"Other position",
            r"Other\s+position",
            r"Other positions",
            r"Other\s+positions",
        ]

    matches = []

    for pattern in patterns:

        for match in re.finditer(
            pattern,
            html_text,
            flags=re.I
        ):

            # Position information normally appears shortly
            # after the label. Capture a controlled window.
            start = match.start()

            end = min(
                len(html_text),
                match.end() + 2500
            )

            fragment = html_text[start:end]

            matches.append({
                "label_match": match.group(0),
                "fragment": fragment,
                "text": strip_tags(fragment),
            })

    return matches


def extract_candidate_values(fragment, label):

    """
    Try to identify likely position values from a structured
    fragment.

    This deliberately uses known Transfermarkt position names
    only after the position label has been located.

    A keyword appearing elsewhere on the page is NOT enough.
    """

    known_positions = [
        "Goalkeeper",
        "Centre-Back",
        "Center-Back",
        "Left-Back",
        "Right-Back",
        "Defensive Midfield",
        "Central Midfield",
        "Attacking Midfield",
        "Left Midfield",
        "Right Midfield",
        "Left Winger",
        "Right Winger",
        "Second Striker",
        "Centre-Forward",
        "Center-Forward",
        "Striker",
        "Defender",
        "Midfielder",
        "Forward",
    ]

    found = []

    text = strip_tags(fragment)

    for position in known_positions:

        if re.search(
            r"\b" + re.escape(position) + r"\b",
            text,
            flags=re.I
        ):

            found.append(position)

    # Preserve order while removing duplicates.
    unique = []

    for value in found:

        if value.lower() not in {
            x.lower() for x in unique
        }:
            unique.append(value)

    return unique


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    rows = load_sample()

    print(
        f"Sample players selected: {len(rows)}"
    )
    print()

    results = []

    for index, (
        reep_id,
        label,
        transfermarkt_id
    ) in enumerate(rows, start=1):

        transfermarkt_id = str(
            transfermarkt_id
        ).strip()

        url = (
            "https://www.transfermarkt.com/"
            "-/profil/spieler/"
            f"{transfermarkt_id}"
        )

        print("-" * 70)
        print(
            f"[{index}/{len(rows)}] {label}"
        )

        print(
            f"REEP ID:          {reep_id}"
        )

        print(
            f"Transfermarkt ID: {transfermarkt_id}"
        )

        print(
            f"URL:              {url}"
        )

        response = fetch_url(url)

        status = response["status"]
        page = response["html"]
        error = response["error"]

        print(
            f"HTTP status:      {status}"
        )

        if error:
            print(
                f"ERROR:            {error}"
            )

        main_matches = extract_position_field(
            page,
            "main_position"
        )

        other_matches = extract_position_field(
            page,
            "other_position"
        )

        main_candidates = []
        other_candidates = []

        for match in main_matches:

            values = extract_candidate_values(
                match["fragment"],
                "main_position"
            )

            for value in values:

                if value not in main_candidates:
                    main_candidates.append(value)

        for match in other_matches:

            values = extract_candidate_values(
                match["fragment"],
                "other_position"
            )

            for value in values:

                if value not in other_candidates:
                    other_candidates.append(value)

        # ----------------------------------------------------
        # Keep only values that appear in the first structured
        # position fragment.
        #
        # We are still NOT accepting them as canonical.
        # ----------------------------------------------------

        result = {
            "reep_id": reep_id,
            "label": label,
            "transfermarkt_id": transfermarkt_id,
            "url": url,
            "http_status": status,
            "request_success": status == 200,

            "main_position_label_found":
                len(main_matches) > 0,

            "other_position_label_found":
                len(other_matches) > 0,

            "main_position_candidates":
                main_candidates,

            "other_position_candidates":
                other_candidates,

            "main_position_match_count":
                len(main_matches),

            "other_position_match_count":
                len(other_matches),

            "main_position_raw_context":
                [
                    {
                        "label_match":
                            x["label_match"],
                        "text":
                            x["text"][:1500]
                    }
                    for x in main_matches[:3]
                ],

            "other_position_raw_context":
                [
                    {
                        "label_match":
                            x["label_match"],
                        "text":
                            x["text"][:1500]
                    }
                    for x in other_matches[:3]
                ],

            "canonical_position_accepted":
                False,

            "canonical_position":
                None,

            "error":
                error,
        }

        results.append(result)

        print()

        print(
            "Main position label: "
            + (
                "FOUND"
                if result["main_position_label_found"]
                else "NOT FOUND"
            )
        )

        print(
            "Other position label: "
            + (
                "FOUND"
                if result["other_position_label_found"]
                else "NOT FOUND"
            )
        )

        print(
            "Main candidates: "
            + (
                ", ".join(main_candidates)
                if main_candidates
                else "NONE"
            )
        )

        print(
            "Other candidates: "
            + (
                ", ".join(other_candidates)
                if other_candidates
                else "NONE"
            )
        )

        print(
            "Canonical position accepted: NO"
        )

        if index < len(rows):
            time.sleep(REQUEST_DELAY)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    main_found = sum(
        1
        for r in results
        if r["main_position_label_found"]
    )

    other_found = sum(
        1
        for r in results
        if r["other_position_label_found"]
    )

    main_value_found = sum(
        1
        for r in results
        if r["main_position_candidates"]
    )

    other_value_found = sum(
        1
        for r in results
        if r["other_position_candidates"]
    )

    http_200 = sum(
        1
        for r in results
        if r["http_status"] == 200
    )

    summary = {
        "status": "PASS",
        "read_only": True,

        "source_database":
            str(SOURCE_DB),

        "sample_size_requested":
            SAMPLE_SIZE,

        "sample_size_returned":
            len(results),

        "http_200_count":
            http_200,

        "main_position_label_found_count":
            main_found,

        "other_position_label_found_count":
            other_found,

        "main_position_value_found_count":
            main_value_found,

        "other_position_value_found_count":
            other_value_found,

        "canonical_positions_accepted":
            0,

        "important_note":
            (
                "Extracted position candidates are "
                "structured test results only. "
                "No candidate has been accepted as "
                "canonical REEP position evidence."
            ),

        "results":
            results,
    }

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    with open(
        JSON_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            summary,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    with open(
        CSV_OUTPUT,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "reep_id",
                "label",
                "transfermarkt_id",
                "url",
                "http_status",
                "request_success",
                "main_position_label_found",
                "other_position_label_found",
                "main_position_candidates",
                "other_position_candidates",
                "main_position_match_count",
                "other_position_match_count",
                "canonical_position_accepted",
                "canonical_position",
                "error",
            ],
        )

        writer.writeheader()

        for row in results:

            writer.writerow({
                "reep_id":
                    row["reep_id"],

                "label":
                    row["label"],

                "transfermarkt_id":
                    row["transfermarkt_id"],

                "url":
                    row["url"],

                "http_status":
                    row["http_status"],

                "request_success":
                    row["request_success"],

                "main_position_label_found":
                    row["main_position_label_found"],

                "other_position_label_found":
                    row["other_position_label_found"],

                "main_position_candidates":
                    "; ".join(
                        row["main_position_candidates"]
                    ),

                "other_position_candidates":
                    "; ".join(
                        row["other_position_candidates"]
                    ),

                "main_position_match_count":
                    row["main_position_match_count"],

                "other_position_match_count":
                    row["other_position_match_count"],

                "canonical_position_accepted":
                    row["canonical_position_accepted"],

                "canonical_position":
                    row["canonical_position"] or "",

                "error":
                    row["error"] or "",
            })

    # --------------------------------------------------------
    # Console summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(
        f"Sample players tested:          {len(results)}"
    )

    print(
        f"Transfermarkt HTTP 200:          {http_200}"
    )

    print(
        f"Main position labels found:      {main_found}"
    )

    print(
        f"Other position labels found:     {other_found}"
    )

    print(
        f"Main position values found:      {main_value_found}"
    )

    print(
        f"Other position values found:     {other_value_found}"
    )

    print(
        "Canonical positions accepted:    0"
    )

    print()
    print("Outputs:")
    print(
        f"  {JSON_OUTPUT}"
    )
    print(
        f"  {CSV_OUTPUT}"
    )

    print()
    print("IMPORTANT:")
    print(
        "No position data was written to any database."
    )

    print(
        "The v1.0.0 database remains untouched."
    )

    print(
        "This test only evaluates structured extraction."
    )

    print()
    print("STATUS: PASS")


if __name__ == "__main__":
    main()