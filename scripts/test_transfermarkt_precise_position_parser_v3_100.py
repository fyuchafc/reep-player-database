import csv
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import duckdb


# ============================================================
# REEP — TRANSFERMARKT POSITION PARSER V3
# 100-PLAYER READ-ONLY VALIDATION
# ============================================================

SOURCE_DB = (
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_JSON = Path(
    "output/reep-transfermarkt-position-v3-100-audit.json"
)

OUTPUT_CSV = Path(
    "output/reep-transfermarkt-position-v3-100-audit.csv"
)

SAMPLE_SIZE = 100

DELAY_SECONDS = 1.0

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)


# ============================================================
# KNOWN TRANSFERMARKT POSITION VALUES
# ============================================================

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


# ============================================================
# CLEAN HTML
# ============================================================

def clean_html_text(value):

    if value is None:
        return ""

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = value.replace(
        "&nbsp;",
        " "
    )

    value = value.replace(
        "&amp;",
        "&"
    )

    value = value.replace(
        "&quot;",
        '"'
    )

    value = value.replace(
        "&#39;",
        "'"
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# FETCH PAGE
# ============================================================

def fetch_page(url):

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

        with urlopen(
            request,
            timeout=30
        ) as response:

            status = response.status

            html = response.read().decode(
                "utf-8",
                errors="replace"
            )

        return status, html, None

    except HTTPError as exc:

        return (
            exc.code,
            "",
            f"HTTPError: {exc}"
        )

    except URLError as exc:

        return (
            None,
            "",
            f"URLError: {exc}"
        )

    except Exception as exc:

        return (
            None,
            "",
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# EXTRACT PRECISE POSITIONS
# ============================================================

def extract_precise_positions(html):

    main_positions = []
    other_positions = []

    exact_main_structure = False
    exact_other_structure = False


    # --------------------------------------------------------
    # MAIN POSITION
    # --------------------------------------------------------

    main_pattern = re.compile(
        r"""
        <dt
            \s+
            class=["']detail-position__title["']
            \s*
        >
            \s*
            Main\s+position:?
            \s*
        </dt>

        (?P<dds>
            (?:
                \s*
                <dd
                    \s+
                    class=["']detail-position__position["']
                    \s*
                >
                    .*?
                </dd>
            )+
        )
        """,
        re.IGNORECASE |
        re.DOTALL |
        re.VERBOSE,
    )


    # --------------------------------------------------------
    # OTHER POSITIONS
    # --------------------------------------------------------

    other_pattern = re.compile(
        r"""
        <dt
            \s+
            class=["']detail-position__title["']
            \s*
        >
            \s*
            Other\s+position:?
            \s*
        </dt>

        (?P<dds>
            (?:
                \s*
                <dd
                    \s+
                    class=["']detail-position__position["']
                    \s*
                >
                    .*?
                </dd>
            )+
        )
        """,
        re.IGNORECASE |
        re.DOTALL |
        re.VERBOSE,
    )


    # --------------------------------------------------------
    # MAIN
    # --------------------------------------------------------

    for match in main_pattern.finditer(html):

        exact_main_structure = True

        dds_html = match.group("dds")

        values = re.findall(
            r"""
            <dd
                \s+
                class=["']detail-position__position["']
                \s*
            >
                (.*?)
            </dd>
            """,
            dds_html,
            re.IGNORECASE |
            re.DOTALL |
            re.VERBOSE,
        )

        for raw_value in values:

            value = clean_html_text(
                raw_value
            )

            if value in KNOWN_POSITIONS:

                main_positions.append(
                    value
                )


    # --------------------------------------------------------
    # OTHER
    # --------------------------------------------------------

    for match in other_pattern.finditer(html):

        exact_other_structure = True

        dds_html = match.group("dds")

        values = re.findall(
            r"""
            <dd
                \s+
                class=["']detail-position__position["']
                \s*
            >
                (.*?)
            </dd>
            """,
            dds_html,
            re.IGNORECASE |
            re.DOTALL |
            re.VERBOSE,
        )

        for raw_value in values:

            value = clean_html_text(
                raw_value
            )

            if value in KNOWN_POSITIONS:

                other_positions.append(
                    value
                )


    # --------------------------------------------------------
    # FALLBACK MAIN
    # --------------------------------------------------------

    if not exact_main_structure:

        fallback_main = re.compile(
            r"""
            <dt
                [^>]*?
                class=["']detail-position__title["']
                [^>]*?
            >
                \s*
                Main\s+position:?
                \s*
            </dt>
            \s*
            <dd
                [^>]*?
                class=["']detail-position__position["']
                [^>]*?
            >
                \s*
                (.*?)
                \s*
            </dd>
            """,
            re.IGNORECASE |
            re.DOTALL |
            re.VERBOSE,
        )

        for match in fallback_main.finditer(html):

            value = clean_html_text(
                match.group(1)
            )

            if value in KNOWN_POSITIONS:

                main_positions.append(
                    value
                )

                exact_main_structure = True


    # --------------------------------------------------------
    # FALLBACK OTHER
    # --------------------------------------------------------

    if not exact_other_structure:

        fallback_other = re.compile(
            r"""
            <dt
                [^>]*?
                class=["']detail-position__title["']
                [^>]*?
            >
                \s*
                Other\s+position:?
                \s*
            </dt>

            (?P<dds>
                (?:
                    \s*
                    <dd
                        [^>]*?
                        class=["']detail-position__position["']
                        [^>]*?
                    >
                        .*?
                    </dd>
                )+
            )
            """,
            re.IGNORECASE |
            re.DOTALL |
            re.VERBOSE,
        )

        for match in fallback_other.finditer(html):

            dds_html = match.group("dds")

            values = re.findall(
                r"""
                <dd
                    [^>]*?
                    class=["']detail-position__position["']
                    [^>]*?
                >
                    (.*?)
                </dd>
                """,
                dds_html,
                re.IGNORECASE |
                re.DOTALL |
                re.VERBOSE,
            )

            found_any = False

            for raw_value in values:

                value = clean_html_text(
                    raw_value
                )

                if value in KNOWN_POSITIONS:

                    other_positions.append(
                        value
                    )

                    found_any = True

            if found_any:

                exact_other_structure = True


    # --------------------------------------------------------
    # REMOVE DUPLICATES
    # --------------------------------------------------------

    main_positions = list(
        dict.fromkeys(
            main_positions
        )
    )

    other_positions = list(
        dict.fromkeys(
            other_positions
        )
    )


    return {
        "main_positions": main_positions,
        "other_positions": other_positions,
        "exact_main_structure":
            exact_main_structure,
        "exact_other_structure":
            exact_other_structure,
    }


# ============================================================
# LOAD 100 PLAYERS
# ============================================================

def load_sample_players():

    con = duckdb.connect(
        SOURCE_DB,
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
            b.provider = 'transfermarkt'
            AND b.namespace = 'spieler'
            AND b.external_id IS NOT NULL
            AND TRIM(
                CAST(
                    b.external_id AS VARCHAR
                )
            ) <> ''

        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY p.reep_id
            ORDER BY
                b.rung ASC,
                b.external_id
        ) = 1

        ORDER BY p.reep_id

        LIMIT ?
    """

    rows = con.execute(
        query,
        [SAMPLE_SIZE]
    ).fetchall()

    con.close()

    return rows


# ============================================================
# SAVE RESULTS
# ============================================================

def save_outputs(results, summary):

    OUTPUT_JSON.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    payload = {
        "summary": summary,
        "results": results,
    }


    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            indent=2,
            ensure_ascii=False
        )


    fieldnames = [
        "index",
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
        encoding="utf-8-sig"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()


        for row in results:

            writer.writerow({
                "index":
                    row["index"],

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

                "main_position":
                    row["main_position"],

                "other_positions":
                    "; ".join(
                        row["other_positions"]
                    ),

                "exact_main_structure":
                    row[
                        "exact_main_structure"
                    ],

                "exact_other_structure":
                    row[
                        "exact_other_structure"
                    ],

                "result":
                    row["result"],

                "error":
                    row["error"] or "",
            })


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print(
        "REEP TRANSFERMARKT POSITION PARSER V3"
    )
    print(
        "100-PLAYER READ-ONLY VALIDATION"
    )
    print("=" * 80)
    print()

    print(
        "READ-ONLY TEST"
    )

    print(
        "The REEP source database "
        "will NOT be modified."
    )

    print()

    print(
        "Source database:"
    )

    print(
        SOURCE_DB
    )

    print()

    print(
        "Loading Transfermarkt sample..."
    )

    players = load_sample_players()

    print(
        f"Sample size requested: "
        f"{SAMPLE_SIZE}"
    )

    print(
        f"Sample players found:  "
        f"{len(players)}"
    )

    print()


    results = []

    http_200 = 0
    fetch_failures = 0

    main_found = 0
    other_found = 0

    exact_main = 0
    exact_other = 0

    no_position = 0

    unexpected_main = 0
    unexpected_other = 0

    main_position_counts = {}
    other_position_counts = {}


    for index, row in enumerate(
        players,
        start=1
    ):

        reep_id = row[0]
        label = row[1]

        transfermarkt_id = str(
            row[2]
        ).strip()


        url = (
            "https://www.transfermarkt.com/"
            f"-/profil/spieler/"
            f"{transfermarkt_id}"
        )


        print(
            f"[{index}/{len(players)}] "
            f"{label}"
        )


        status, html, error = fetch_page(
            url
        )


        if status == 200:

            http_200 += 1


        if (
            status == 200
            and html
        ):

            extracted = (
                extract_precise_positions(
                    html
                )
            )


            main_positions = (
                extracted[
                    "main_positions"
                ]
            )

            other_positions = (
                extracted[
                    "other_positions"
                ]
            )

            exact_main_structure = (
                extracted[
                    "exact_main_structure"
                ]
            )

            exact_other_structure = (
                extracted[
                    "exact_other_structure"
                ]
            )


            if main_positions:

                main_found += 1

            if other_positions:

                other_found += 1

            if exact_main_structure:

                exact_main += 1

            if exact_other_structure:

                exact_other += 1


            # ----------------------------------------------
            # COUNT MAIN POSITIONS
            # ----------------------------------------------

            for position in main_positions:

                main_position_counts[
                    position
                ] = (
                    main_position_counts.get(
                        position,
                        0
                    ) + 1
                )


            # ----------------------------------------------
            # COUNT OTHER POSITIONS
            # ----------------------------------------------

            for position in other_positions:

                other_position_counts[
                    position
                ] = (
                    other_position_counts.get(
                        position,
                        0
                    ) + 1
                )


            # ----------------------------------------------
            # RESULT
            # ----------------------------------------------

            if main_positions:

                result = "PASS"

            else:

                result = (
                    "NO_POSITION_FOUND"
                )

                no_position += 1


        else:

            main_positions = []

            other_positions = []

            exact_main_structure = False
            exact_other_structure = False

            result = "FETCH_FAILED"

            fetch_failures += 1


        results.append({

            "index":
                index,

            "reep_id":
                reep_id,

            "label":
                label,

            "transfermarkt_id":
                transfermarkt_id,

            "url":
                url,

            "http_status":
                status,

            "main_position":
                (
                    main_positions[0]
                    if main_positions
                    else None
                ),

            "other_positions":
                other_positions,

            "exact_main_structure":
                exact_main_structure,

            "exact_other_structure":
                exact_other_structure,

            "result":
                result,

            "error":
                error,
        })


        time.sleep(
            DELAY_SECONDS
        )


    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {

        "sample_size_requested":
            SAMPLE_SIZE,

        "players_tested":
            len(players),

        "http_200":
            http_200,

        "fetch_failures":
            fetch_failures,

        "main_position_found":
            main_found,

        "other_position_found":
            other_found,

        "exact_main_structures":
            exact_main,

        "exact_other_structures":
            exact_other,

        "no_position_found":
            no_position,

        "main_position_counts":
            dict(
                sorted(
                    main_position_counts.items(),
                    key=lambda item: (
                        -item[1],
                        item[0]
                    )
                )
            ),

        "other_position_counts":
            dict(
                sorted(
                    other_position_counts.items(),
                    key=lambda item: (
                        -item[1],
                        item[0]
                    )
                )
            ),

        "validation_rules": {

            "sample_size":
                "100 players",

            "database":
                "read-only",

            "position_parser":
                "exact Transfermarkt structure",

            "broad_keyword_search":
                False,

            "multiple_other_positions":
                True,

            "source_database_modified":
                False,
        },
    }


    save_outputs(
        results,
        summary
    )


    # ========================================================
    # FINAL REPORT
    # ========================================================

    print()

    print("=" * 80)
    print(
        "FINAL 100-PLAYER VALIDATION REPORT"
    )
    print("=" * 80)

    print()

    print(
        f"Players tested:             "
        f"{len(players)}"
    )

    print(
        f"HTTP 200:                   "
        f"{http_200}"
    )

    print(
        f"Main position found:        "
        f"{main_found}"
    )

    print(
        f"Other position found:       "
        f"{other_found}"
    )

    print(
        f"Exact main structures:      "
        f"{exact_main}"
    )

    print(
        f"Exact other structures:     "
        f"{exact_other}"
    )

    print(
        f"No position found:          "
        f"{no_position}"
    )

    print(
        f"Fetch failures:             "
        f"{fetch_failures}"
    )

    print()

    print(
        "MAIN POSITION DISTRIBUTION:"
    )

    if main_position_counts:

        for position, count in sorted(
            main_position_counts.items(),
            key=lambda item: (
                -item[1],
                item[0]
            )
        ):

            print(
                f"  {position}: {count}"
            )

    else:

        print(
            "  NONE"
        )


    print()

    print(
        "OTHER POSITION DISTRIBUTION:"
    )

    if other_position_counts:

        for position, count in sorted(
            other_position_counts.items(),
            key=lambda item: (
                -item[1],
                item[0]
            )
        ):

            print(
                f"  {position}: {count}"
            )

    else:

        print(
            "  NONE"
        )


    print()

    print(
        "OUTPUT FILES:"
    )

    print(
        OUTPUT_JSON
    )

    print(
        OUTPUT_CSV
    )

    print()


    # ========================================================
    # PASS / REVIEW
    # ========================================================

    if (
        len(players) == SAMPLE_SIZE
        and http_200 == SAMPLE_SIZE
        and fetch_failures == 0
        and main_found >= 70
    ):

        print("=" * 80)
        print(
            "STATUS: PASS — 100-PLAYER "
            "POSITION VALIDATION"
        )
        print("=" * 80)

        print()

        print(
            "Transfermarkt position extraction "
            "passed the 100-player validation."
        )

        print(
            "No fetch failures occurred."
        )

        print(
            "The source REEP database remained "
            "read-only."
        )

        print()

        print(
            "NEXT STEP:"
        )

        print(
            "Review the audit results before "
            "full-scale extraction."
        )

        print(
            "Do NOT modify v1.0.0."
        )


    else:

        print("=" * 80)
        print(
            "STATUS: REVIEW REQUIRED"
        )
        print("=" * 80)

        print()

        print(
            "The 100-player validation did not "
            "meet the current threshold."
        )

        print(
            "Do NOT scale to the full database."
        )


if __name__ == "__main__":

    main()