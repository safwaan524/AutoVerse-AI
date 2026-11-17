
import sqlite3
from pathlib import Path

# Database location
DB_PATH = Path(__file__).parent / "autoverse.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def get_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table'
    """)

    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    return tables


def search_vehicles(query, limit=10):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
    """)

    tables = [row[0] for row in cursor.fetchall()]

    results = []

    for table in tables:
        try:
            cursor.execute(f'SELECT * FROM "{table}" LIMIT 0')
            columns = [item[0] for item in cursor.description]

            searchable = [
                col for col in columns
                if any(word in col.lower()
                       for word in ["brand", "model", "name", "city"])
            ]

            if not searchable:
                continue

            conditions = " OR ".join(
                f'CAST("{col}" AS TEXT) LIKE ?'
                for col in searchable
            )

            sql = f'SELECT * FROM "{table}" WHERE {conditions} LIMIT ?'

            cursor.execute(
                sql,
                [f"%{query}%"] * len(searchable) + [limit]
            )

            rows = cursor.fetchall()

            for row in rows:
                results.append({
                    "table": table,
                    "columns": columns,
                    "data": row
                })

        except sqlite3.Error:
            continue

    conn.close()
    return results


if __name__ == "__main__":
    print("===== AUTOVERSE DATABASE =====")

    print("\nAvailable tables:")
    for table in get_tables():
        print("-", table)

    print("\nBMW search test:")
    results = search_vehicles("BMW")

    for item in results[:5]:
        print(item)

    print("\n===== DATABASE TEST COMPLETE =====")
