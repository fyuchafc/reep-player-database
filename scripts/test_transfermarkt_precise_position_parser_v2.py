import csv
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import duckdb


# ============================================================
# REEP TRANSFERMARKT PRECISE POSITION PARSER V2
# ============================================================
#
# READ-ONLY TEST
#
# This script:
#   1. Reads 10 REEP players with Transfermarkt IDs
#   2. Opens their public Transfermarkt profiles
#   3. Uses the exact HTML structure confirmed from inspection:
#
#      <dt class="detail-position__title">Main position:</dt>
#      <dd class="detail-position__position">Right-Back</dd>
#
#   4. Extracts:
#        - Main position
#        - Other positions
#
#   5. Does NOT modify the REEP source database.
#
# ============================================================


SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_JSON = Path(
    "output/reep-transfermarkt-precise-position-v2-test.json"
)

OUTPUT_CSV = Path(
    "output/reep-transfermarkt-precise-position-v2-test.csv"
)

SAMPLE_SIZE = 10

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)

DELAY_SECONDS = 1.0


# ------------------------------------------------------------
# Position class names we expect from Transfermarkt
# ------------------------------------------------------------

KNOWN_POSITIONS = {
    "Goalkeeper",

    "Centre-Back",
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
}


def clean_html_text(value):
    """Convert HTML text to clean plain text."""
    if value is None:
        return ""

    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("&nbsp;", " ")
    value = value.replace("&amp;", "&")
    value = value.replace("&quot;", '"')
    value = value.replace("&#39;", "'")

    value = re.sub(r"\s+", " ", value)

    return value.strip()


def fetch_page(url):
    """Fetch a public Transfermarkt page."""
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urlopen(request, timeout=30) as response:
            status = response.status
            html = response.read().decode(
                "utf-8",
                errors="replace"
            )

        return status, html, None

    except HTTPError as exc:
        return exc.code, "", f"HTTPError: {exc}"

    except URLError as exc:
        return None, "", f"URLError: {exc}"

    except Exception as exc:
        return None, "", f"{type(exc).__name__}: {exc}"


def extract_exact_positions(html):
    """
    Extract positions ONLY from the confirmed
    detail-position structure.

    Main position:

        <dt class="detail-position__title">
            Main position:
        </dt>
        <dd class="detail-position__position">
            Right-Back
        </dd>

    Other positions:

        <dt class="detail-position__title">
            Other position:
        </dt>
        <dd class="detail-position__position">
            Central Midfield
        </dd>
    """

    main_positions = []
    other_positions = []

    # --------------------------------------------------------
    # Exact main-position structure
    # --------------------------------------------------------

    main_pattern = re.compile(
        r'<dt\s+class=["\']detail-position__title["\']'
        r'\s*>\s*Main\s+position:?\s*</dt>'
        r'\s*'
        r'<dd\s+class=["\']detail-position__position["\']'
        r'\s*>\s*(.*?)\s*</dd>',
        re.IGNORECASE | re.DOTALL,
    )

    # --------------------------------------------------------
    # Exact other-position structure
    # --------------------------------------------------------

    other_pattern = re.compile(
        r'<dt\s+class=["\']detail-position__title["\']'
        r'\s*>\s*Other\s+position:?\s*</dt>'
        r'\s*'
        r'<dd\s+class=["\']detail-position__position["\']'
        r'\s*>\s*(.*?)\s*</dd>',
        re.IGNORECASE | re.DOTALL,
    )

    for match in main_pattern.finditer(html):
        value = clean_html_text(match.group(1))

        if value in KNOWN_POSITIONS:
            main_positions.append(value)

    for match in other_pattern.finditer(html):
        value = clean_html_text(match.group(1))

        if value in KNOWN_POSITIONS:
            other_positions.append(value)

    # Remove duplicates while preserving order
    main_positions = list(dict.fromkeys(main_positions))
    other_positions = list(dict.fromkeys(other_positions))

    # --------------------------------------------------------
    # Detect whether exact structure exists even if value
    # is not one of our known positions.
    # --------------------------------------------------------

    exact_main_structure = bool(
        main_pattern.search(html)
    )

    exact_other_structure = bool(
        other_pattern.search(html)
    )

    return {
        "main_positions": main_positions,
        "other_positions": other_positions,
        "exact_main_structure": exact_main_structure,
        "exact_other_structure": exact_other_structure,
    }


def load_sample_players():
    """Load REEP players with Transfermarkt IDs."""

    con = duckdb.connect(
        SOURCE_DB,
        read_only=True,
    )

    query = """
        SELECT
            p.reep_id,
            p.label,
            b.external_id AS transfermarkt_id
        FROM players p
        INNER JOIN bridges b
            ON b.reep_id = p.reep_id
        WHERE
            b.provider = 'transfermarkt'
            AND b.namespace = 'spieler'
            AND b.external_id IS NOT NULL
            AND TRIM(CAST(b.external_id AS VARCHAR)) <> ''
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY p.reep_id
            ORDER BY b.rung ASC, b.external_id
        ) = 1
        ORDER BY p.reep_id
        LIMIT ?
    """

    rows = con.execute(
        query,
        [SAMPLE_SIZE],
    ).fetchall()

    con.close()

    return rows


def save_outputs(results):
    OUTPUT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False,
        )

    fieldnames = [
        "reep_id",
        "label",
        "transfermarkt_id",
        "url",
        "http_status",
        "main_position",
        "other_positions",
        "exact_main_structure",
        "exact_other_structure",
        "result",
        "error",
    ]

    with open(
        OUTPUT_CSV,
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in results:
            writer.writerow({
                "reep_id": row["reep_id"],
                "label": row["label"],
                "transfermarkt_id": row["transfermarkt_id"],
                "url": row["url"],
                "http_status": row["http_status"],
                "main_position": row["main_position"],
                "other_positions": "; ".join(
                    row["other_positions"]
                ),
                "exact_main_structure": row[
                    "exact_main_structure"
                ],
                "exact_other_structure": row[
                    "exact_other_structure"
                ],
                "result": row["result"],
                "error": row["error"] or "",
            })


def main():

    print("=" * 80)
    print("REEP TRANSFERMARKT PRECISE POSITION PARSER V2")
    print("=" * 80)
    print()
    print("READ-ONLY TEST")
    print("The REEP source database will NOT be modified.")
    print()
    print("Source database:")
    print(SOURCE_DB)
    print()

    print("Loading Transfermarkt sample...")

    players = load_sample_players()

    print(f"Sample size requested: {SAMPLE_SIZE}")
    print(f"Sample players found:  {len(players)}")
    print()

    results = []

    http_200 = 0
    main_found = 0
    other_found = 0
    exact_matches = 0
    no_position = 0
    failures = 0

    for index, row in enumerate(players, start=1):

        reep_id = row[0]
        label = row[1]
        transfermarkt_id = str(row[2]).strip()

        url = (
            "https://www.transfermarkt.com/"
            "-/profil/spieler/"
            f"{transfermarkt_id}"
        )

        print("-" * 80)
        print(
            f"PLAYER {index}: {label}"
        )
        print(f"REEP ID: {reep_id}")
        print(f"TRANSFERMARKT ID: {transfermarkt_id}")
        print(f"URL: {url}")
        print()

        status, html, error = fetch_page(url)

        if status == 200:
            http_200 += 1

        if status == 200 and html:

            extracted = extract_exact_positions(
                html
            )

            main_positions = extracted[
                "main_positions"
            ]

            other_positions = extracted[
                "other_positions"
            ]

            exact_main = extracted[
                "exact_main_structure"
            ]

            exact_other = extracted[
                "exact_other_structure"
            ]

            exact_match = (
                exact_main
                and (
                    bool(main_positions)
                    or not exact_main
                )
            )

            if main_positions:
                main_found += 1

            if other_positions:
                other_found += 1

            if exact_main:
                exact_matches += 1

            if main_positions:
                result = "PASS"
            else:
                result = "NO_POSITION_FOUND"
                no_position += 1

        else:

            main_positions = []
            other_positions = []
            exact_main = False
            exact_other = False
            exact_match = False

            result = "FETCH_FAILED"
            failures += 1

        print(
            f"HTTP STATUS: {status}"
        )

        print(
            "EXACT MAIN STRUCTURE:",
            exact_main
        )

        print(
            "EXACT OTHER STRUCTURE:",
            exact_other
        )

        print()

        print(
            "MAIN POSITION:",
            (
                main_positions[0]
                if main_positions
                else "NONE"
            )
        )

        print(
            "OTHER POSITIONS:"
        )

        if other_positions:
            for position in other_positions:
                print(f"  - {position}")
        else:
            print("  NONE")

        print()

        print(
            f"RESULT: {result}"
        )

        results.append({
            "reep_id": reep_id,
            "label": label,
            "transfermarkt_id": transfermarkt_id,
            "url": url,
            "http_status": status,
            "main_position": (
                main_positions[0]
                if main_positions
                else None
            ),
            "other_positions": other_positions,
            "exact_main_structure": exact_main,
            "exact_other_structure": exact_other,
            "result": result,
            "error": error,
        })

        time.sleep(DELAY_SECONDS)

    save_outputs(results)

    print()
    print("=" * 80)
    print("FINAL TEST REPORT")
    print("=" * 80)
    print()
    print(
        f"Players tested:             {len(players)}"
    )
    print(
        f"HTTP 200:                   {http_200}"
    )
    print(
        f"Main position found:        {main_found}"
    )
    print(
        f"Other position found:       {other_found}"
    )
    print(
        f"Exact main structures:      {exact_matches}"
    )
    print(
        f"No position found:          {no_position}"
    )
    print(
        f"Fetch failures:             {failures}"
    )
    print()
    print("OUTPUT FILES:")
    print(OUTPUT_JSON)
    print(OUTPUT_CSV)
    print()

    if (
        len(players) == SAMPLE_SIZE
        and http_200 == SAMPLE_SIZE
        and main_found > 0
        and failures == 0
    ):
        print("=" * 80)
        print("STATUS: PASS — PRECISE STRUCTURE WORKING")
        print("=" * 80)
        print()
        print(
            "The parser is extracting positions from the "
            "confirmed Transfermarkt HTML structure."
        )
        print(
            "This is still a 10-player validation only."
        )
        print(
            "Do NOT scale to the full database yet."
        )

    else:
        print("=" * 80)
        print("STATUS: REVIEW REQUIRED")
        print("=" * 80)
        print()
        print(
            "The precise parser did not pass the "
            "minimum validation requirements."
        )
        print(
            "Do NOT scale this parser yet."
        )


if __name__ == "__main__":
    main()