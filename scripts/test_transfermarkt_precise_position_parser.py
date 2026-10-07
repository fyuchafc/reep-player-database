"""
REEP PLAYER DATABASE
Transfermarkt Precise Position Parser — 10 Player Test

PURPOSE
-------
Read-only test of precise Transfermarkt position extraction.

This script:
1. Reads the REEP source database READ-ONLY.
2. Finds REEP players with Transfermarkt player IDs.
3. Tests 10 players.
4. Downloads their public Transfermarkt profile pages.
5. Extracts positions ONLY from the exact HTML structure:

   <dt class="detail-position__title">Main position:</dt>
   <dd class="detail-position__position">...</dd>

   <dt class="detail-position__title">Other position:</dt>
   <dd class="detail-position__position">...</dd>

6. Does NOT modify the REEP source database.
7. Does NOT write anything to the master database.

OUTPUT
------
output/reep-transfermarkt-precise-position-test.json
output/reep-transfermarkt-precise-position-test.csv
"""

from __future__ import annotations

import csv
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import duckdb


# ============================================================
# PATHS
# ============================================================

SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main\data"
    r"\reep-register-v1.duckdb"
)

OUTPUT_DIR = Path("output")

JSON_OUTPUT = OUTPUT_DIR / "reep-transfermarkt-precise-position-test.json"
CSV_OUTPUT = OUTPUT_DIR / "reep-transfermarkt-precise-position-test.csv"


# ============================================================
# TEST SETTINGS
# ============================================================

SAMPLE_SIZE = 10

REQUEST_TIMEOUT = 30

REQUEST_DELAY_SECONDS = 2.0

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)


# ============================================================
# HELPERS
# ============================================================

def clean_html_text(value: str) -> str:
    """
    Convert HTML entities and remove remaining HTML tags.
    """
    if not value:
        return ""

    value = re.sub(r"<[^>]+>", " ", value)

    replacements = {
        "&nbsp;": " ",
        "&amp;": "&",
        "&quot;": '"',
        "&#39;": "'",
        "&lt;": "<",
        "&gt;": ">",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def extract_precise_positions(html: str) -> tuple[str | None, list[str], dict]:
    """
    Extract positions from the exact Transfermarkt structure.

    We deliberately avoid searching the entire page for position names.

    Expected structure:

        <dt class="detail-position__title">Main position:</dt>
        <dd class="detail-position__position">Attacking Midfield</dd>

    and:

        <dt class="detail-position__title">Other position:</dt>
        <dd class="detail-position__position">Right Winger</dd>
        <dd class="detail-position__position">Central Midfield</dd>

    Returns:
        main_position
        other_positions
        diagnostics
    """

    diagnostics = {
        "main_label_found": False,
        "other_label_found": False,
        "main_value_count": 0,
        "other_value_count": 0,
        "exact_structure_match": False,
    }

    main_position = None
    other_positions: list[str] = []

    # --------------------------------------------------------
    # MAIN POSITION
    #
    # We locate the exact <dt> label and then inspect the
    # following <dd> within the same <dl>.
    # --------------------------------------------------------

    main_pattern = re.compile(
        r"""
        <dl\b[^>]*>
        \s*
        <dt\b
            [^>]*class=["'][^"']*detail-position__title[^"']*["']
            [^>]*>
            \s*Main\s+position:\s*
        </dt>
        \s*
        <dd\b
            [^>]*class=["'][^"']*detail-position__position[^"']*["']
            [^>]*>
            (.*?)
        </dd>
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )

    main_match = main_pattern.search(html)

    if main_match:
        diagnostics["main_label_found"] = True

        value = clean_html_text(main_match.group(1))

        if value:
            main_position = value
            diagnostics["main_value_count"] = 1

    # --------------------------------------------------------
    # OTHER POSITIONS
    #
    # Locate the exact <dl> whose <dt> says "Other position:"
    # and then collect its position <dd> elements.
    # --------------------------------------------------------

    other_pattern = re.compile(
        r"""
        <dl\b[^>]*>
        \s*
        <dt\b
            [^>]*class=["'][^"']*detail-position__title[^"']*["']
            [^>]*>
            \s*Other\s+position:\s*
        </dt>
        (?P<body>.*?)
        </dl>
        """,
        re.IGNORECASE | re.DOTALL | re.VERBOSE,
    )

    other_match = other_pattern.search(html)

    if other_match:
        diagnostics["other_label_found"] = True

        body = other_match.group("body")

        value_pattern = re.compile(
            r"""
            <dd\b
                [^>]*class=["'][^"']*detail-position__position[^"']*["']
                [^>]*>
                (.*?)
            </dd>
            """,
            re.IGNORECASE | re.DOTALL | re.VERBOSE,
        )

        for match in value_pattern.finditer(body):
            value = clean_html_text(match.group(1))

            if value and value not in other_positions:
                other_positions.append(value)

        diagnostics["other_value_count"] = len(other_positions)

    # --------------------------------------------------------
    # EXACT STRUCTURE VALIDATION
    # --------------------------------------------------------

    diagnostics["exact_structure_match"] = (
        main_position is not None
        or len(other_positions) > 0
    )

    return main_position, other_positions, diagnostics


def fetch_url(url: str) -> tuple[int | None, str | None, str | None]:
    """
    Fetch a public URL.

    Returns:
        status_code
        html
        error
    """

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        },
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            status_code = response.getcode()

            raw = response.read()

            html = raw.decode("utf-8", errors="replace")

            return status_code, html, None

    except HTTPError as exc:
        return exc.code, None, f"HTTPError: {exc}"

    except URLError as exc:
        return None, None, f"URLError: {exc}"

    except Exception as exc:
        return None, None, f"{type(exc).__name__}: {exc}"


def get_transfermarkt_sample() -> list[dict]:
    """
    Read 10 REEP players with Transfermarkt IDs.

    This is READ-ONLY.
    """

    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Source database not found:\n{SOURCE_DB}"
        )

    connection = duckdb.connect(
        str(SOURCE_DB),
        read_only=True,
    )

    try:
        query = """
            SELECT DISTINCT
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
                AND TRIM(b.external_id) <> ''
            ORDER BY
                p.reep_id
            LIMIT ?
        """

        rows = connection.execute(
            query,
            [SAMPLE_SIZE],
        ).fetchall()

        results = []

        for reep_id, label, transfermarkt_id in rows:
            results.append(
                {
                    "reep_id": reep_id,
                    "label": label,
                    "transfermarkt_id": str(transfermarkt_id).strip(),
                }
            )

        return results

    finally:
        connection.close()


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 80)
    print("REEP TRANSFERMARKT PRECISE POSITION PARSER TEST")
    print("=" * 80)
    print()
    print("READ-ONLY TEST")
    print("The REEP source database will NOT be modified.")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Source database:")
    print(SOURCE_DB)
    print()

    print("Loading Transfermarkt sample...")
    sample = get_transfermarkt_sample()

    print(f"Sample size requested: {SAMPLE_SIZE}")
    print(f"Sample players found:  {len(sample)}")
    print()

    if not sample:
        print("FAIL: No Transfermarkt players found.")
        return

    results = []

    for index, player in enumerate(sample, start=1):

        reep_id = player["reep_id"]
        label = player["label"]
        transfermarkt_id = player["transfermarkt_id"]

        url = (
            "https://www.transfermarkt.com/"
            f"-/profil/spieler/{transfermarkt_id}"
        )

        print("-" * 80)
        print(f"PLAYER {index}: {label}")
        print(f"REEP ID: {reep_id}")
        print(f"TRANSFERMARKT ID: {transfermarkt_id}")
        print(f"URL: {url}")
        print()

        result = {
            "reep_id": reep_id,
            "label": label,
            "transfermarkt_id": transfermarkt_id,
            "url": url,
            "http_status": None,
            "main_position": None,
            "other_positions": [],
            "other_position_count": 0,
            "main_label_found": False,
            "other_label_found": False,
            "main_value_count": 0,
            "other_value_count": 0,
            "exact_structure_match": False,
            "status": "NOT_TESTED",
            "error": None,
        }

        status_code, html, error = fetch_url(url)

        result["http_status"] = status_code

        if error:
            result["error"] = error
            result["status"] = "FETCH_FAILED"

            print(f"HTTP STATUS: {status_code}")
            print(f"ERROR: {error}")

        elif not html:
            result["status"] = "EMPTY_RESPONSE"
            result["error"] = "Empty HTML response"

            print(f"HTTP STATUS: {status_code}")
            print("ERROR: Empty HTML response")

        else:

            (
                main_position,
                other_positions,
                diagnostics,
            ) = extract_precise_positions(html)

            result["main_position"] = main_position
            result["other_positions"] = other_positions
            result["other_position_count"] = len(other_positions)

            result["main_label_found"] = diagnostics[
                "main_label_found"
            ]

            result["other_label_found"] = diagnostics[
                "other_label_found"
            ]

            result["main_value_count"] = diagnostics[
                "main_value_count"
            ]

            result["other_value_count"] = diagnostics[
                "other_value_count"
            ]

            result["exact_structure_match"] = diagnostics[
                "exact_structure_match"
            ]

            if main_position:
                result["status"] = "PASS"
            elif result["other_positions"]:
                result["status"] = "PARTIAL"
            else:
                result["status"] = "NO_POSITION_FOUND"

            print(f"HTTP STATUS: {status_code}")

            print(
                "MAIN LABEL FOUND: "
                f"{result['main_label_found']}"
            )

            print(
                "OTHER LABEL FOUND: "
                f"{result['other_label_found']}"
            )

            print(
                "EXACT STRUCTURE MATCH: "
                f"{result['exact_structure_match']}"
            )

            print()

            print(
                "MAIN POSITION: "
                f"{main_position if main_position else 'NONE'}"
            )

            if other_positions:
                print("OTHER POSITIONS:")

                for position in other_positions:
                    print(f"  - {position}")

            else:
                print("OTHER POSITIONS: NONE")

            print()
            print(f"RESULT: {result['status']}")

        results.append(result)

        if index < len(sample):
            time.sleep(REQUEST_DELAY_SECONDS)

    # ========================================================
    # VALIDATION
    # ========================================================

    total = len(results)

    http_200 = sum(
        1
        for r in results
        if r["http_status"] == 200
    )

    main_found = sum(
        1
        for r in results
        if r["main_position"]
    )

    exact_matches = sum(
        1
        for r in results
        if r["exact_structure_match"]
    )

    no_position = sum(
        1
        for r in results
        if r["status"] == "NO_POSITION_FOUND"
    )

    fetch_failed = sum(
        1
        for r in results
        if r["status"] == "FETCH_FAILED"
    )

    # ========================================================
    # SAVE JSON
    # ========================================================

    report = {
        "test": "Transfermarkt precise position parser",
        "read_only": True,
        "source_database": str(SOURCE_DB),
        "sample_size_requested": SAMPLE_SIZE,
        "sample_size_tested": total,
        "summary": {
            "http_200": http_200,
            "main_position_found": main_found,
            "exact_structure_matches": exact_matches,
            "no_position_found": no_position,
            "fetch_failed": fetch_failed,
        },
        "results": results,
    }

    JSON_OUTPUT.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # SAVE CSV
    # ========================================================

    with CSV_OUTPUT.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        fieldnames = [
            "reep_id",
            "label",
            "transfermarkt_id",
            "url",
            "http_status",
            "main_position",
            "other_positions",
            "other_position_count",
            "main_label_found",
            "other_label_found",
            "main_value_count",
            "other_value_count",
            "exact_structure_match",
            "status",
            "error",
        ]

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for result in results:
            row = result.copy()

            row["other_positions"] = "; ".join(
                result["other_positions"]
            )

            writer.writerow(row)

    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()
    print("=" * 80)
    print("FINAL TEST REPORT")
    print("=" * 80)
    print()

    print(f"Players tested:             {total}")
    print(f"HTTP 200:                   {http_200}")
    print(f"Main position found:        {main_found}")
    print(f"Exact structure matches:    {exact_matches}")
    print(f"No position found:          {no_position}")
    print(f"Fetch failures:             {fetch_failed}")
    print()

    print("OUTPUT FILES:")
    print(JSON_OUTPUT)
    print(CSV_OUTPUT)
    print()

    if total == SAMPLE_SIZE and http_200 == total and main_found == total:
        print("=" * 80)
        print("STATUS: PASS")
        print("=" * 80)
        print()
        print(
            "The precise Transfermarkt position structure was successfully "
            "parsed for all test players."
        )
        print()
        print(
            "This parser is now a strong candidate for the next "
            "larger-scale position extraction test."
        )

    else:
        print("=" * 80)
        print("STATUS: REVIEW REQUIRED")
        print("=" * 80)
        print()
        print(
            "The parser did not obtain a main position for every "
            "test player."
        )
        print(
            "Do NOT scale this parser yet. Review the CSV/JSON results."
        )


if __name__ == "__main__":
    main()