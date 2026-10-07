import csv
import json
import random
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

INPUT_CSV = "output/reep-transfermarkt-position-v3-100-audit.csv"

OUTPUT_JSON = "output/reep-transfermarkt-position-v4-25-audit.json"
OUTPUT_CSV = "output/reep-transfermarkt-position-v4-25-audit.csv"

TEST_COUNT = 25

MIN_DELAY = 10
MAX_DELAY = 15

MAX_RETRIES = 3

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)


def clean_text(value):
    if not value:
        return ""

    value = re.sub(r"\s+", " ", value)
    return value.strip()


def fetch_html(url):

    last_error = ""

    for attempt in range(1, MAX_RETRIES + 1):

        try:

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "text/html,application/xhtml+xml,"
                        "application/xml;q=0.9,image/avif,"
                        "image/webp,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                status = response.getcode()
                raw = response.read()

                # Handle gzip if needed.
                if raw[:2] == b"\x1f\x8b":

                    import gzip

                    raw = gzip.decompress(raw)

                html = raw.decode(
                    "utf-8",
                    errors="replace"
                )

                return {
                    "status": status,
                    "html": html,
                    "bytes": len(raw),
                    "error": "",
                    "attempts": attempt,
                }

        except urllib.error.HTTPError as e:

            last_error = (
                f"HTTPError: HTTP Error "
                f"{e.code}: {e.reason}"
            )

            if e.code == 403:

                if attempt < MAX_RETRIES:

                    wait = 20 * attempt

                    print(
                        f"      HTTP 403. "
                        f"Waiting {wait}s before retry..."
                    )

                    time.sleep(wait)

            else:

                if attempt < MAX_RETRIES:

                    wait = 10 * attempt

                    print(
                        f"      HTTP {e.code}. "
                        f"Waiting {wait}s before retry..."
                    )

                    time.sleep(wait)

        except Exception as e:

            last_error = (
                f"{type(e).__name__}: {str(e)}"
            )

            if attempt < MAX_RETRIES:

                wait = 10 * attempt

                print(
                    f"      {type(e).__name__}. "
                    f"Waiting {wait}s before retry..."
                )

                time.sleep(wait)

    return {
        "status": None,
        "html": "",
        "bytes": 0,
        "error": last_error,
        "attempts": MAX_RETRIES,
    }


def extract_positions(html):

    main_positions = []
    other_positions = []

    # Exact Transfermarkt structure.
    #
    # Main:
    # <dt class="detail-position__title">
    # Main position:
    # </dt>
    # <dd class="detail-position__position">
    # Attacking Midfield
    # </dd>
    #
    # Other:
    # <dt class="detail-position__title">
    # Other position:
    # </dt>
    # <dd class="detail-position__position">
    # Right Winger
    # </dd>
    # <dd class="detail-position__position">
    # Central Midfield
    # </dd>

    pattern = re.compile(
        r'<dt[^>]*class=["\'][^"\']*detail-position__title[^"\']*'
        r'["\'][^>]*>\s*'
        r'(Main position|Other position)\s*:?\s*'
        r'</dt>'
        r'(?P<body>.*?)'
        r'(?=<dt[^>]*class=["\'][^"\']*detail-position__title'
        r'|</dl>|</div>\s*</div>\s*</div>)',
        re.IGNORECASE | re.DOTALL
    )

    for match in pattern.finditer(html):

        label = clean_text(match.group(1))
        body = match.group("body")

        values = re.findall(
            r'<dd[^>]*class=["\'][^"\']*detail-position__position'
            r'[^"\']*["\'][^>]*>\s*(.*?)\s*</dd>',
            body,
            re.IGNORECASE | re.DOTALL
        )

        cleaned_values = []

        for value in values:

            value = re.sub(
                r"<[^>]+>",
                " ",
                value
            )

            value = clean_text(value)

            if value and value not in cleaned_values:

                cleaned_values.append(value)

        if label.lower() == "main position":

            main_positions.extend(
                cleaned_values
            )

        elif label.lower() == "other position":

            other_positions.extend(
                cleaned_values
            )

    # Remove duplicates while preserving order.
    main_positions = list(
        dict.fromkeys(main_positions)
    )

    other_positions = list(
        dict.fromkeys(other_positions)
    )

    return main_positions, other_positions


def main():

    print("=" * 80)
    print("TRANSFERMARKT PRECISE POSITION PARSER V4 — 25 PLAYER VALIDATION")
    print("=" * 80)
    print()

    print("READ-ONLY TEST")
    print("- No REEP database changes")
    print("- No v1.0.0 changes")
    print("- 25 Transfermarkt pages")
    print("- Exact position HTML extraction")
    print("- Slow randomized request interval")
    print()

    players = []

    with open(
        INPUT_CSV,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            tm_id = row["transfermarkt_id"].strip()

            if not tm_id:
                continue

            players.append(row)

            if len(players) >= TEST_COUNT:
                break

    print(
        f"Selected players: {len(players)}"
    )
    print()

    results = []

    main_counter = Counter()
    other_counter = Counter()

    http_200 = 0
    http_403 = 0
    fetch_failures = 0
    main_found = 0
    other_found = 0
    exact_main = 0
    exact_other = 0
    no_position = 0

    for index, row in enumerate(
        players,
        start=1
    ):

        reep_id = row["reep_id"].strip()
        label = row["label"].strip()
        tm_id = row["transfermarkt_id"].strip()

        url = (
            "https://www.transfermarkt.com/"
            f"spieler/profil/spieler/{tm_id}"
        )

        print(
            f"[{index}/{len(players)}] {label}"
        )

        print(
            f"      REEP ID: {reep_id}"
        )

        print(
            f"      TM ID: {tm_id}"
        )

        fetched = fetch_html(url)

        status = fetched["status"]
        html = fetched["html"]

        main_positions = []
        other_positions = []

        if status == 200:

            http_200 += 1

            print(
                f"      HTTP 200 "
                f"({fetched['bytes']} bytes)"
            )

            main_positions, other_positions = (
                extract_positions(html)
            )

            if main_positions:

                main_found += 1
                exact_main += 1

                for position in main_positions:

                    main_counter[position] += 1

            if other_positions:

                other_found += 1
                exact_other += 1

                for position in other_positions:

                    other_counter[position] += 1

            if (
                not main_positions
                and not other_positions
            ):

                no_position += 1

                print(
                    "      Position block: NOT FOUND"
                )

            else:

                if main_positions:

                    print(
                        "      Main: "
                        + ", ".join(main_positions)
                    )

                if other_positions:

                    print(
                        "      Other: "
                        + ", ".join(other_positions)
                    )

        else:

            if status == 403:

                http_403 += 1

            else:

                fetch_failures += 1

            print(
                f"      FETCH FAILURE: "
                f"HTTP {status} | "
                f"{fetched['error']}"
            )

        results.append({
            "index": index,
            "reep_id": reep_id,
            "label": label,
            "transfermarkt_id": tm_id,
            "url": url,
            "http_status": status,
            "bytes": fetched["bytes"],
            "attempts": fetched["attempts"],
            "main_positions": main_positions,
            "other_positions": other_positions,
            "main_position_count": len(main_positions),
            "other_position_count": len(other_positions),
            "error": fetched["error"],
        })

        if index < len(players):

            wait = random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )

            print(
                f"      Waiting "
                f"{wait:.1f}s..."
            )

            time.sleep(wait)

        print()

    # Validation.
    total = len(results)

    if total:

        http_200_rate = (
            http_200 / total
        ) * 100

        main_rate = (
            main_found / total
        ) * 100

    else:

        http_200_rate = 0
        main_rate = 0

    # PASS requires:
    # - all 25 fetched successfully
    # - no 403
    # - at least 70% exact main-position extraction
    status = "PASS"

    if http_200 != total:
        status = "REVIEW REQUIRED"

    elif main_rate < 70:
        status = "REVIEW REQUIRED"

    # JSON output.
    output = {
        "test": (
            "Transfermarkt precise position parser V4 "
            "25-player validation"
        ),
        "read_only": True,
        "players_tested": total,
        "http_200": http_200,
        "http_403": http_403,
        "fetch_failures": fetch_failures,
        "http_200_rate_percent": round(
            http_200_rate,
            2
        ),
        "main_position_found": main_found,
        "main_position_rate_percent": round(
            main_rate,
            2
        ),
        "other_position_found": other_found,
        "exact_main_structures": exact_main,
        "exact_other_structures": exact_other,
        "no_position_found": no_position,
        "main_position_distribution": dict(
            main_counter
        ),
        "other_position_distribution": dict(
            other_counter
        ),
        "status": status,
        "results": results,
    }

    Path(
        OUTPUT_JSON
    ).write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )

    # CSV output.
    fieldnames = [
        "index",
        "reep_id",
        "label",
        "transfermarkt_id",
        "url",
        "http_status",
        "bytes",
        "attempts",
        "main_positions",
        "other_positions",
        "main_position_count",
        "other_position_count",
        "error",
    ]

    with open(
        OUTPUT_CSV,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()

        for result in results:

            row = dict(result)

            row["main_positions"] = (
                " | ".join(
                    result["main_positions"]
                )
            )

            row["other_positions"] = (
                " | ".join(
                    result["other_positions"]
                )
            )

            writer.writerow(row)

    print("=" * 80)
    print("FINAL VALIDATION RESULT")
    print("=" * 80)

    print(
        f"Players tested: {total}"
    )

    print(
        f"HTTP 200: {http_200}"
    )

    print(
        f"HTTP 403: {http_403}"
    )

    print(
        f"Other fetch failures: "
        f"{fetch_failures}"
    )

    print(
        f"HTTP 200 rate: "
        f"{http_200_rate:.2f}%"
    )

    print(
        f"Main position found: "
        f"{main_found}"
    )

    print(
        f"Main position rate: "
        f"{main_rate:.2f}%"
    )

    print(
        f"Other position found: "
        f"{other_found}"
    )

    print(
        f"Exact main structures: "
        f"{exact_main}"
    )

    print(
        f"Exact other structures: "
        f"{exact_other}"
    )

    print(
        f"No position found: "
        f"{no_position}"
    )

    print()

    print("MAIN POSITION DISTRIBUTION")
    print("-" * 80)

    for position, count in sorted(
        main_counter.items(),
        key=lambda x: (-x[1], x[0])
    ):

        print(
            f"{position}: {count}"
        )

    print()

    print("OTHER POSITION DISTRIBUTION")
    print("-" * 80)

    for position, count in sorted(
        other_counter.items(),
        key=lambda x: (-x[1], x[0])
    ):

        print(
            f"{position}: {count}"
        )

    print()

    print(
        f"STATUS: {status}"
    )

    print()

    print(
        f"Saved: {OUTPUT_JSON}"
    )

    print(
        f"Saved: {OUTPUT_CSV}"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()