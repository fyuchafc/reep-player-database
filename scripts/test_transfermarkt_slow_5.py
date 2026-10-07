import csv
import json
import random
import time
import urllib.request
import urllib.error
from pathlib import Path

INPUT_CSV = "output/reep-transfermarkt-position-v3-100-audit.csv"

OUTPUT_JSON = "output/reep-transfermarkt-slow-5-test.json"
OUTPUT_CSV = "output/reep-transfermarkt-slow-5-test.csv"

TEST_COUNT = 5

# Slow request interval.
MIN_DELAY = 8
MAX_DELAY = 12

# Retry settings.
MAX_RETRIES = 3

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)


def fetch_page(url):
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
                html = response.read()

                return {
                    "status": status,
                    "bytes": len(html),
                    "error": "",
                    "attempts": attempt
                }

        except urllib.error.HTTPError as e:

            last_error = f"HTTPError: HTTP Error {e.code}: {e.reason}"

            if e.code == 403:

                # Longer cooldown after forbidden response.
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
        "bytes": 0,
        "error": last_error,
        "attempts": MAX_RETRIES
    }


def main():

    print("=" * 80)
    print("TRANSFERMARKT SLOW 5-PLAYER ACCESS TEST")
    print("=" * 80)
    print()

    print("IMPORTANT:")
    print("- Read-only test")
    print("- No REEP database changes")
    print("- No v1.0.0 changes")
    print("- Only 5 Transfermarkt pages will be tested")
    print("- Requests are deliberately slow")
    print()

    rows = []

    with open(
        INPUT_CSV,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            if row["transfermarkt_id"].strip():

                rows.append(row)

            if len(rows) >= TEST_COUNT:
                break

    if not rows:

        print("ERROR: No Transfermarkt IDs found.")
        return

    results = []

    print(
        f"Selected players: {len(rows)}"
    )
    print()

    for index, row in enumerate(rows, start=1):

        label = row["label"].strip()
        tm_id = row["transfermarkt_id"].strip()

        url = (
            f"https://www.transfermarkt.com/"
            f"spieler/profil/spieler/{tm_id}"
        )

        print(
            f"[{index}/{len(rows)}] "
            f"{label}"
        )

        print(
            f"      TM ID: {tm_id}"
        )

        print(
            f"      URL: {url}"
        )

        result = fetch_page(url)

        record = {
            "index": index,
            "reep_id": row["reep_id"],
            "label": label,
            "transfermarkt_id": tm_id,
            "url": url,
            "http_status": result["status"],
            "bytes": result["bytes"],
            "attempts": result["attempts"],
            "error": result["error"],
        }

        results.append(record)

        if result["status"] == 200:

            print(
                f"      RESULT: HTTP 200 "
                f"({result['bytes']} bytes)"
            )

        else:

            print(
                f"      RESULT: "
                f"HTTP {result['status']} | "
                f"{result['error']}"
            )

        if index < len(rows):

            wait = random.uniform(
                MIN_DELAY,
                MAX_DELAY
            )

            print(
                f"      Waiting "
                f"{wait:.1f}s before next request..."
            )

            time.sleep(wait)

        print()

    # Save JSON.
    output = {
        "test": "Transfermarkt slow 5-player access test",
        "read_only": True,
        "players_tested": len(results),
        "http_200": sum(
            1 for r in results
            if r["http_status"] == 200
        ),
        "http_403": sum(
            1 for r in results
            if r["http_status"] == 403
        ),
        "other_failures": sum(
            1 for r in results
            if r["http_status"] not in (200, 403)
        ),
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

    # Save CSV.
    fieldnames = [
        "index",
        "reep_id",
        "label",
        "transfermarkt_id",
        "url",
        "http_status",
        "bytes",
        "attempts",
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
        writer.writerows(results)

    http_200 = output["http_200"]
    http_403 = output["http_403"]

    print("=" * 80)
    print("FINAL RESULT")
    print("=" * 80)

    print(
        f"Players tested: {len(results)}"
    )

    print(
        f"HTTP 200: {http_200}"
    )

    print(
        f"HTTP 403: {http_403}"
    )

    print(
        f"Other failures: "
        f"{output['other_failures']}"
    )

    print()

    if http_200 == len(results):

        print(
            "STATUS: PASS"
        )

        print(
            "Transfermarkt access recovered "
            "for the slow 5-player test."
        )

    elif http_200 > 0:

        print(
            "STATUS: PARTIAL"
        )

        print(
            "Transfermarkt is accessible "
            "but still intermittently blocking requests."
        )

    else:

        print(
            "STATUS: FAIL"
        )

        print(
            "Transfermarkt is still blocking "
            "the requests."
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