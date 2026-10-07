import csv
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

import duckdb


# ============================================================
# REEP — TRANSFERMARKT POSITION STRUCTURE INSPECTION
# ============================================================
#
# READ-ONLY TEST
#
# Purpose:
#   Inspect the actual public Transfermarkt HTML structure for
#   10 real REEP players with Transfermarkt IDs.
#
# IMPORTANT:
#   This script DOES NOT accept keyword matches as position
#   evidence. It only identifies the HTML area containing
#   possible position fields for manual/structured validation.
#
# Source database:
#   REEP source DB, opened READ-ONLY
#
# Outputs:
#   output/reep-transfermarkt-position-structure-test.json
#   output/reep-transfermarkt-position-structure-test.csv
#
# No database is modified.
# ============================================================


SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

OUTPUT_DIR = Path("output")

JSON_OUTPUT = OUTPUT_DIR / "reep-transfermarkt-position-structure-test.json"
CSV_OUTPUT = OUTPUT_DIR / "reep-transfermarkt-position-structure-test.csv"

SAMPLE_SIZE = 10
REQUEST_DELAY = 2.0
TIMEOUT = 30

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/154.0.0.0 Safari/537.36"
)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clean_html(text):
    if not text:
        return ""

    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)

    return text


def html_to_text(text):
    if not text:
        return ""

    text = clean_html(text)

    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(?:div|p|li|tr|td|th|section|article|h1|h2|h3|h4|h5|h6)>",
                  "\n",
                  text,
                  flags=re.I)

    text = re.sub(r"<[^>]+>", " ", text)

    text = re.sub(r"&nbsp;", " ", text, flags=re.I)
    text = re.sub(r"&amp;", "&", text, flags=re.I)
    text = re.sub(r"&quot;", '"', text, flags=re.I)
    text = re.sub(r"&#39;", "'", text, flags=re.I)

    text = re.sub(r"\s+", " ", text)

    return text.strip()


def extract_context(html, pattern, context=1200):
    matches = list(re.finditer(pattern, html, flags=re.I))

    snippets = []

    for match in matches[:10]:
        start = max(0, match.start() - context)
        end = min(len(html), match.end() + context)

        snippet = html[start:end]

        snippets.append({
            "match": match.group(0),
            "html_snippet": snippet,
            "text_snippet": html_to_text(snippet),
        })

    return snippets


def detect_position_labels(text):
    patterns = [
        r"Main position",
        r"Other position",
        r"Other positions",
        r"Hauptposition",
        r"Nebenposition",
        r"Nebenpositionen",
        r"Position:",
        r"Position",
    ]

    found = []

    for pattern in patterns:
        if re.search(pattern, text, flags=re.I):
            found.append(pattern)

    return found


def extract_position_candidates(text):
    """
    This is intentionally conservative.

    We only extract text immediately surrounding recognised
    position labels. We DO NOT declare any extracted value
    canonical.
    """

    patterns = [
        r"Main position",
        r"Other position",
        r"Other positions",
        r"Hauptposition",
        r"Nebenposition",
        r"Nebenpositionen",
    ]

    results = []

    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.I):
            start = max(0, match.start() - 150)
            end = min(len(text), match.end() + 500)

            context = text[start:end]

            results.append({
                "label_match": match.group(0),
                "context": context
            })

    return results[:20]


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
        with urlopen(request, timeout=TIMEOUT) as response:
            status = response.getcode()
            body = response.read()

            encoding = response.headers.get_content_charset() or "utf-8"

            try:
                html = body.decode(encoding, errors="replace")
            except Exception:
                html = body.decode("utf-8", errors="replace")

            return {
                "status": status,
                "html": html,
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
            "error": f"{type(exc).__name__}: {exc}",
        }


# ------------------------------------------------------------
# Read sample from REEP
# ------------------------------------------------------------

def load_sample():
    print("=" * 70)
    print("REEP — TRANSFERMARKT POSITION STRUCTURE INSPECTION")
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
            AND TRIM(CAST(b.external_id AS VARCHAR)) <> ''
        GROUP BY
            p.reep_id,
            p.label,
            b.external_id
        ORDER BY
            p.reep_id
        LIMIT ?
    """

    rows = con.execute(query, [SAMPLE_SIZE]).fetchall()

    con.close()

    return rows


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows = load_sample()

    print(f"Sample players selected: {len(rows)}")
    print()

    results = []

    for index, (reep_id, label, transfermarkt_id) in enumerate(rows, start=1):

        transfermarkt_id = str(transfermarkt_id).strip()

        url = (
            "https://www.transfermarkt.com/"
            "-/profil/spieler/"
            f"{transfermarkt_id}"
        )

        print("-" * 70)
        print(f"[{index}/{len(rows)}] {label}")
        print(f"REEP ID:          {reep_id}")
        print(f"Transfermarkt ID: {transfermarkt_id}")
        print(f"URL:              {url}")

        result = fetch_url(url)

        http_status = result["status"]
        html = result["html"]
        error = result["error"]

        print(f"HTTP status:      {http_status}")

        if error:
            print(f"ERROR:            {error}")

        html_length = len(html)

        print(f"HTML characters:  {html_length:,}")

        clean_text = html_to_text(html)

        position_labels = detect_position_labels(clean_text)

        candidates = extract_position_candidates(clean_text)

        structured_context = []

        patterns = [
            r"Main position",
            r"Other position",
            r"Other positions",
            r"Hauptposition",
            r"Nebenposition",
            r"Nebenpositionen",
        ]

        for pattern in patterns:
            structured_context.extend(
                extract_context(html, pattern, context=1500)
            )

        # Remove duplicate snippets
        seen = set()
        unique_context = []

        for item in structured_context:
            key = item["html_snippet"]

            if key in seen:
                continue

            seen.add(key)
            unique_context.append(item)

        result_row = {
            "reep_id": reep_id,
            "label": label,
            "transfermarkt_id": transfermarkt_id,
            "url": url,
            "http_status": http_status,
            "request_success": http_status == 200,
            "html_characters": html_length,
            "position_labels_found": position_labels,
            "position_label_count": len(position_labels),
            "candidate_contexts": candidates,
            "structured_html_contexts": unique_context[:20],
            "error": error,
            "canonical_position_accepted": False,
            "canonical_position": None,
        }

        results.append(result_row)

        if position_labels:
            print(
                "Position labels found: "
                + ", ".join(position_labels)
            )
        else:
            print("Position labels found: NONE")

        print(
            f"Structured HTML contexts: "
            f"{len(unique_context[:20])}"
        )

        print(
            "Canonical position accepted: NO "
            "(inspection only)"
        )

        if index < len(rows):
            time.sleep(REQUEST_DELAY)

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    summary = {
        "status": "PASS",
        "read_only": True,
        "source_database": str(SOURCE_DB),
        "sample_size_requested": SAMPLE_SIZE,
        "sample_size_returned": len(rows),
        "http_200_count": sum(
            1 for r in results if r["http_status"] == 200
        ),
        "position_label_found_count": sum(
            1 for r in results
            if r["position_label_count"] > 0
        ),
        "canonical_positions_accepted": 0,
        "important_note": (
            "This test identifies structured Transfermarkt position "
            "areas only. No extracted position is accepted as "
            "canonical evidence."
        ),
        "results": results,
    }

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
                "html_characters",
                "position_labels_found",
                "position_label_count",
                "canonical_position_accepted",
                "canonical_position",
                "error",
            ],
        )

        writer.writeheader()

        for row in results:
            writer.writerow({
                "reep_id": row["reep_id"],
                "label": row["label"],
                "transfermarkt_id": row["transfermarkt_id"],
                "url": row["url"],
                "http_status": row["http_status"],
                "request_success": row["request_success"],
                "html_characters": row["html_characters"],
                "position_labels_found": "; ".join(
                    row["position_labels_found"]
                ),
                "position_label_count": row["position_label_count"],
                "canonical_position_accepted":
                    row["canonical_position_accepted"],
                "canonical_position":
                    row["canonical_position"] or "",
                "error": row["error"] or "",
            })

    # --------------------------------------------------------
    # Final console summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)

    print(f"Sample players tested:       {len(results)}")

    print(
        "Transfermarkt HTTP 200:     "
        f"{summary['http_200_count']}"
    )

    print(
        "Position labels located:     "
        f"{summary['position_label_found_count']}"
    )

    print(
        "Canonical positions accepted: 0"
    )

    print()
    print("Outputs:")
    print(f"  {JSON_OUTPUT}")
    print(f"  {CSV_OUTPUT}")

    print()
    print("IMPORTANT:")
    print(
        "No position has been added to the REEP database."
    )
    print(
        "No v1.0.0 database has been modified."
    )
    print(
        "This is an HTML structure inspection only."
    )

    print()
    print("STATUS: PASS")


if __name__ == "__main__":
    main()