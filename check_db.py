import sqlite3

DB_PATH = "gartan_availability.db"

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    print("--- Tables in the database ---")
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = c.fetchall()
    for table in tables:
        print(table[0])
    print("\n" + "=" * 30 + "\n")

    print("--- Row Counts ---")
    for table_name in [t[0] for t in tables if t[0] != "sqlite_sequence"]:
        c.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = c.fetchone()[0]
        print(f"{table_name}: {count} rows")
    print("\n" + "=" * 30 + "\n")

    print("--- Sample from crew (first 5 rows) ---")
    c.execute("SELECT * FROM crew LIMIT 5;")
    rows = c.fetchall()
    if not rows:
        print("No data in crew table.")
    for row in rows:
        print(row)
    print("\n" + "=" * 30 + "\n")

    print("--- Sample from appliance (first 5 rows) ---")
    c.execute("SELECT * FROM appliance LIMIT 5;")
    rows = c.fetchall()
    if not rows:
        print("No data in appliance table.")
    for row in rows:
        print(row)
    print("\n" + "=" * 30 + "\n")

    print("--- Sample from crew_availability (first 5 rows) ---")
    c.execute("SELECT * FROM crew_availability LIMIT 5;")
    rows = c.fetchall()
    if not rows:
        print("No data in crew_availability table.")
    for row in rows:
        print(row)
    print("\n" + "=" * 30 + "\n")

    print("--- Sample from appliance_availability (first 5 rows) ---")
    c.execute("SELECT * FROM appliance_availability LIMIT 5;")
    rows = c.fetchall()
    if not rows:
        print("No data in appliance_availability table.")
    for row in rows:
        print(row)
    print("\n" + "=" * 30 + "\n")

except sqlite3.Error as e:
    print(f"Database error: {e}")
finally:
    if conn:
        conn.close()
