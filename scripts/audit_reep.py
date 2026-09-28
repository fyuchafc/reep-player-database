"""Read-only audit of a REEP DuckDB database.

Usage:
    python scripts/audit_reep.py "C:\\path\\to\\reep-register-v1.duckdb"

The script never writes to the source database.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


def audit(db_path: Path) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    print("=" * 80)
    print("REEP REGISTER — READ-ONLY AUDIT")
    print("=" * 80)
    print(f"Database: {db_path}")
    print(f"Size: {db_path.stat().st_size / (1024 * 1024):,.2f} MB")

    con = duckdb.connect(str(db_path), read_only=True)

    try:
        tables = con.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
            """
        ).fetchall()

        print("\n" + "=" * 80)
        print("TABLES")
        print("=" * 80)

        if not tables:
            print("No user tables found.")
            return

        for schema, table in tables:
            print(f"\n[{schema}.{table}]")

            columns = con.execute(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = ? AND table_name = ?
                ORDER BY ordinal_position
                """,
                [schema, table],
            ).fetchall()

            print("\nColumns:")
            for name, dtype, nullable in columns:
                print(f"  {name:<40} {dtype:<25} nullable={nullable}")

            qualified = f'"{schema}"."{table}"'
            row_count = con.execute(
                f"SELECT COUNT(*) FROM {qualified}"
            ).fetchone()[0]

            print(f"\nRows: {row_count:,}")

            print("\nSample (up to 5 rows):")
            rows = con.execute(
                f"SELECT * FROM {qualified} LIMIT 5"
            ).fetchall()

            for row in rows:
                print(" ", row)

    finally:
        con.close()

    print("\n" + "=" * 80)
    print("AUDIT COMPLETE — SOURCE DATABASE WAS NOT MODIFIED")
    print("=" * 80)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only audit of a REEP DuckDB database."
    )
    parser.add_argument(
        "database",
        type=Path,
        help="Path to reep-register-v1.duckdb",
    )
    args = parser.parse_args()
    audit(args.database)


if __name__ == "__main__":
    main()
