
import sqlite3

conn = sqlite3.connect("autoverse.db")
cursor = conn.cursor()

tables = [
    "brands",
    "models",
    "variants",
    "prices",
    "cities",
    "used_listings"
]

print("\n========== AUTOVERSE DATABASE TEST ==========")

for table in tables:
    print(f"\nTABLE: {table}")

    cursor.execute(f'PRAGMA table_info("{table}")')
    columns = cursor.fetchall()

    print("COLUMNS:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

    cursor.execute(f'SELECT * FROM "{table}" LIMIT 2')
    rows = cursor.fetchall()

    print("\nSAMPLE RECORDS:")
    for row in rows:
        print(row)

print("\n========== TEST COMPLETED ==========")

conn.close()
