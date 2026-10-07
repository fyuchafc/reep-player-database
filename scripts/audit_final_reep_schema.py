import duckdb
from pathlib import Path

# ================================================================
# CONFIGURATION
# ================================================================

SOURCE_DB = Path(
    r"C:\Users\ADMIN\OneDrive\Documents\important database files"
    r"\fyucha-player-database-main\fyucha-player-database-main"
    r"\data\reep-register-v1.duckdb"
)

WORKING_DIR = Path("output")

POSITION_DB = (
    WORKING_DIR /
    "reep-player-position-evidence.duckdb"
)

# ================================================================
# HELPERS
# ================================================================

def print_header(title):

    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def inspect_database(path, label):

    print_header(label)

    print(f"Database: {path}")

    if not path.exists():

        print("STATUS: FILE NOT FOUND")
        return

    print("STATUS: FOUND")

    con = duckdb.connect(
        str(path),
        read_only=True
    )

    tables = con.execute("""
        SELECT
            table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name
    """).fetchall()

    print()
    print(f"Tables: {len(tables)}")

    for (table_name,) in tables:

        print()
        print("-" * 80)
        print(f"TABLE: {table_name}")
        print("-" * 80)

        columns = con.execute("""
            SELECT
                column_name,
                data_type,
                is_nullable
            FROM information_schema.columns
            WHERE
                table_schema = 'main'
                AND table_name = ?
            ORDER BY ordinal_position
        """, [table_name]).fetchall()

        for column_name, data_type, nullable in columns:

            print(
                f"  {column_name:<30} "
                f"{data_type:<25} "
                f"nullable={nullable}"
            )

        try:

            count = con.execute(
                f'SELECT COUNT(*) FROM "{table_name}"'
            ).fetchone()[0]

            print()
            print(f"  ROW COUNT: {count:,}")

        except Exception as exc:

            print(
                f"  ROW COUNT: ERROR — {exc}"
            )

    con.close()


# ================================================================
# MAIN
# ================================================================

def main():

    print("=" * 80)
    print("REEP FINAL SCHEMA — DATABASE INVENTORY AUDIT")
    print("=" * 80)

    print()
    print("READ-ONLY — NO DATABASE WILL BE MODIFIED.")

    print()
    print("Purpose:")
    print(
        "Inventory the authoritative REEP source and the "
        "current position evidence database before designing "
        "the final production schema."
    )

    inspect_database(
        SOURCE_DB,
        "AUTHORITATIVE REEP SOURCE DATABASE"
    )

    inspect_database(
        POSITION_DB,
        "CURRENT POSITION EVIDENCE DATABASE"
    )

    print_header("FINAL SCHEMA INVENTORY COMPLETE")

    print()
    print("No databases were modified.")
    print()
    print(
        "Paste the complete output into ChatGPT for the "
        "next schema-design step."
    )


if __name__ == "__main__":
    main()