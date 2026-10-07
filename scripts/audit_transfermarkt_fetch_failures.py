import csv
from collections import Counter

INPUT_CSV = "output/reep-transfermarkt-position-v3-100-audit.csv"


def main():
    print("=" * 80)
    print("TRANSFERMARKT 100-PLAYER FETCH FAILURE AUDIT")
    print("=" * 80)
    print()

    print("Reading:")
    print(INPUT_CSV)
    print()

    status_counts = Counter()
    error_counts = Counter()

    failed_rows = []

    with open(
        INPUT_CSV,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        reader = csv.DictReader(f)

        for row in reader:

            status = (
                row["http_status"]
                or ""
            ).strip()

            error = (
                row["error"]
                or ""
            ).strip()

            if status:
                status_counts[status] += 1

            if error:
                error_type = error.split(":")[0].strip()
                error_counts[error_type] += 1

            if status != "200":
                failed_rows.append(row)

    print("HTTP STATUS DISTRIBUTION")
    print("-" * 80)

    for status, count in sorted(
        status_counts.items(),
        key=lambda x: (
            -x[1],
            x[0]
        )
    ):
        print(
            f"{status}: {count}"
        )

    print()

    print("ERROR TYPE DISTRIBUTION")
    print("-" * 80)

    if error_counts:

        for error_type, count in sorted(
            error_counts.items(),
            key=lambda x: (
                -x[1],
                x[0]
            )
        ):
            print(
                f"{error_type}: {count}"
            )

    else:

        print("No recorded errors.")

    print()

    print(
        f"Failed/non-200 rows: "
        f"{len(failed_rows)}"
    )

    print()

    print("FIRST 20 FAILED REQUESTS")
    print("-" * 80)

    for row in failed_rows[:20]:

        print(
            f"{row['index']}. "
            f"{row['label']} | "
            f"TM ID {row['transfermarkt_id']} | "
            f"HTTP {row['http_status']} | "
            f"{row['error']}"
        )

    print()

    print("=" * 80)

    if (
        "429" in status_counts
        or "HTTPError" in error_counts
    ):
        print(
            "CONCLUSION: REQUEST THROTTLING/BLOCKING "
            "IS LIKELY."
        )

    elif failed_rows:

        print(
            "CONCLUSION: FETCH PROBLEM DETECTED."
        )

    else:

        print(
            "CONCLUSION: NO FETCH FAILURES."
        )

    print("=" * 80)


if __name__ == "__main__":
    main()