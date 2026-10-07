import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import duckdb


# ============================================================
# REEP — TRANSFERMARKT POSITION ELEMENT INSPECTION
# ============================================================
#
# READ-ONLY
#
# Purpose:
#   Inspect the exact HTML immediately surrounding Transfermarkt
#   position fields.
#
# This script DOES NOT:
#   - modify the REEP source database
#   - modify v1.0.0
#   - create a position database
#   - accept any position as canonical
#
# It only helps us identify the exact HTML structure needed for
# a reliable parser.
#
# Output:
#   output/reep-transfermarkt-position-elements.json
#   output/reep-transfermarkt-position-elements.txt
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
    "reep-transfermarkt-position-elements.json"
)

TEXT_OUTPUT = (
    OUTPUT_DIR /
    "reep-transfermarkt-position-elements.txt"
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
# Fetch
# ------------------------------------------------------------

def fetch_page(url):

    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
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

            page = body.decode(
                encoding,
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
            "error": f"HTTPError {exc.code}: {exc.reason}",
        }

    except URLError as exc:

        return {
            "status": None,
            "html": "",
            "error": f"URLError: {exc.reason}",
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

    con = duckdb.connect(
        str(SOURCE_DB),
        read_only=True
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
# HTML inspection
# ------------------------------------------------------------

def find_label_occurrences(page, label):

    results = []

    for match in re.finditer(
        re.escape(label),
        page,
        flags=re.I
    ):

        start = max(
            0,
            match.start() - 1800
        )

        end = min(
            len(page),
            match.end() + 2500
        )

        fragment = page[start:end]

        results.append({
            "label": match.group(0),
            "absolute_start": match.start(),
            "absolute_end": match.end(),
            "html": fragment,
        })

    return results[:5]


def identify_nearby_elements(fragment):

    """
    Try to identify the HTML tags immediately around the label.

    This is diagnostic only.
    """

    findings = []

    # Locate the label again inside the fragment.
    match = re.search(
        r"(Main\s+position|Other\s+position|Other\s+positions)",
        fragment,
        flags=re.I
    )

    if not match:
        return findings

    position = match.start()

    # --------------------------------------------------------
    # Find nearby opening tags before the label.
    # --------------------------------------------------------

    before = fragment[:position]

    opening_tags = list(
        re.finditer(
            r"<([a-zA-Z0-9]+)(?:\s[^>]*)?>",
            before
        )
    )

    nearby_opening = opening_tags[-15:]

    for tag in nearby_opening:

        start = max(
            0,
            tag.start() - 200
        )

        end = min(
            len(fragment),
            tag.end() + 800
        )

        findings.append({
            "type": "nearby_opening_tag",
            "tag": tag.group(0),
            "context": fragment[start:end],
        })

    # --------------------------------------------------------
    # Capture the immediate parent-like blocks.
    # --------------------------------------------------------

    block_patterns = [
        r"<div\b[^>]*>.*?</div>",
        r"<li\b[^>]*>.*?</li>",
        r"<tr\b[^>]*>.*?</tr>",
        r"<dt\b[^>]*>.*?</dt>",
        r"<dd\b[^>]*>.*?</dd>",
        r"<span\b[^>]*>.*?</span>",
    ]

    for pattern in block_patterns:

        for block in re.finditer(
            pattern,
            fragment,
            flags=re.I | re.S
        ):

            if (
                match.start() >= block.start()
                and match.start() <= block.end()
            ):

                block_text = block.group(0)

                if re.search(
                    r"Main\s+position|Other\s+position|Other\s+positions",
                    block_text,
                    flags=re.I
                ):

                    findings.append({
                        "type": "containing_block",
                        "tag": pattern,
                        "context": block_text,
                    })

    return findings


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 70)
    print(
        "REEP — TRANSFERMARKT POSITION ELEMENT INSPECTION"
    )
    print("=" * 70)

    print()
    print(
        "READ-ONLY — source database will NOT be modified."
    )
    print()

    if not SOURCE_DB.exists():
        raise FileNotFoundError(
            f"Source database not found:\n{SOURCE_DB}"
        )

    print(
        "Opening REEP database READ-ONLY..."
    )

    rows = load_sample()

    print(
        f"Sample players selected: {len(rows)}"
    )

    print()

    all_results = []
    text_sections = []

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
            f"Transfermarkt ID: {transfermarkt_id}"
        )

        print(
            f"URL: {url}"
        )

        response = fetch_page(url)

        page = response["html"]

        print(
            f"HTTP status: {response['status']}"
        )

        player_result = {
            "reep_id": reep_id,
            "label": label,
            "transfermarkt_id": transfermarkt_id,
            "url": url,
            "http_status": response["status"],
            "error": response["error"],
            "main_position": [],
            "other_position": [],
        }

        text_sections.append(
            "\n" +
            "=" * 100 +
            "\n" +
            f"PLAYER {index}: {label}\n" +
            f"REEP ID: {reep_id}\n" +
            f"TRANSFERMARKT ID: {transfermarkt_id}\n" +
            f"URL: {url}\n" +
            "=" * 100 +
            "\n"
        )

        if page:

            for field_name, label_pattern in [
                (
                    "main_position",
                    "Main position"
                ),
                (
                    "other_position",
                    "Other position"
                ),
                (
                    "other_position",
                    "Other positions"
                ),
            ]:

                occurrences = find_label_occurrences(
                    page,
                    label_pattern
                )

                for occurrence in occurrences:

                    nearby = identify_nearby_elements(
                        occurrence["html"]
                    )

                    item = {
                        "label_pattern":
                            label_pattern,

                        "label_match":
                            occurrence["label"],

                        "absolute_start":
                            occurrence[
                                "absolute_start"
                            ],

                        "absolute_end":
                            occurrence[
                                "absolute_end"
                            ],

                        "html_context":
                            occurrence["html"],

                        "nearby_elements":
                            nearby,
                    }

                    player_result[
                        field_name
                    ].append(item)

                    text_sections.append(
                        "\n"
                        + f"FIELD: {field_name}\n"
                        + f"LABEL: {label_pattern}\n"
                        + "-" * 80
                        + "\n"
                        + occurrence["html"]
                        + "\n"
                    )

                    if nearby:

                        text_sections.append(
                            "\n"
                            + "NEARBY ELEMENTS\n"
                            + "-" * 80
                            + "\n"
                        )

                        for n, item_nearby in enumerate(
                            nearby,
                            start=1
                        ):

                            text_sections.append(
                                f"\n--- ELEMENT {n} ---\n"
                            )

                            text_sections.append(
                                item_nearby[
                                    "context"
                                ]
                            )

                            text_sections.append(
                                "\n"
                            )

        all_results.append(
            player_result
        )

        if index < len(rows):
            time.sleep(
                REQUEST_DELAY
            )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    output = {
        "status": "PASS",
        "read_only": True,
        "sample_size": len(rows),
        "important_note": (
            "Diagnostic HTML inspection only. "
            "No position values are accepted as canonical."
        ),
        "players": all_results,
    }

    with open(
        JSON_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2
        )

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    with open(
        TEXT_OUTPUT,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(text_sections)
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    main_count = sum(
        len(x["main_position"])
        for x in all_results
    )

    other_count = sum(
        len(x["other_position"])
        for x in all_results
    )

    http_200 = sum(
        1
        for x in all_results
        if x["http_status"] == 200
    )

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(
        f"Players tested:             {len(rows)}"
    )

    print(
        f"HTTP 200:                   {http_200}"
    )

    print(
        f"Main-position HTML matches: {main_count}"
    )

    print(
        f"Other-position matches:     {other_count}"
    )

    print()
    print("Outputs:")
    print(
        f"  {JSON_OUTPUT}"
    )

    print(
        f"  {TEXT_OUTPUT}"
    )

    print()
    print(
        "IMPORTANT: No position was accepted "
        "or written to any database."
    )

    print(
        "STATUS: PASS"
    )


if __name__ == "__main__":
    main()