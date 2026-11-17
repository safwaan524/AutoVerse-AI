
import pandas as pd
import sqlite3
from pathlib import Path

BASE = Path("datasets/tco-india")
DB_PATH = Path("autoverse.db")

def build_database():

    if not BASE.exists():
        print("Dataset folder not found!")
        return

    conn = sqlite3.connect(DB_PATH)

    files = sorted(BASE.rglob("*.parquet"))
    imported = set()

    print("\n===== AUTOVERSE DATABASE BUILDER =====")

    for file in files:

        # Ignore Hugging Face cache files
        if ".cache" in file.parts:
            continue

        table_name = file.stem.lower()

        # Avoid accidental overwriting
        if table_name in imported:
            print("Duplicate table name skipped:", table_name)
            continue

        try:
            df = pd.read_parquet(file)

            df.to_sql(
                table_name,
                conn,
                if_exists="replace",
                index=False
            )

            imported.add(table_name)

            print(f"\nImported: {table_name}")
            print("Records:", len(df))
            print("Columns:", len(df.columns))

        except Exception as e:
            print(f"Error importing {file.name}: {e}")

    print("\n===== DATABASE SUMMARY =====")

    cursor = conn.cursor()

    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()

    for (table,) in tables:
        count = cursor.execute(
            f'SELECT COUNT(*) FROM "{table}"'
        ).fetchone()[0]

        print(f"{table}: {count} records")

    conn.close()

    print("\nDATABASE CREATED:", DB_PATH.resolve())

if __name__ == "__main__":
    build_database()

