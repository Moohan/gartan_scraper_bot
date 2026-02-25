import sqlite3
from datetime import datetime

DB_PATH = "gartan_availability.db"


def check():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("--- Crew Information ---")
    crew_names = ["GIBB, OL", "CASELY, CH", "SABA, JA", "HAYES, JA"]
    placeholders = ",".join("?" * len(crew_names))
    rows = conn.execute(
        f"SELECT * FROM crew WHERE name IN ({placeholders})", crew_names  # nosec B608
    ).fetchall()

    for r in rows:
        print(
            f"ID: {r['id']}, Name: {r['name']}, Role: {r['role']}, Skills: {r['skills']}"
        )

    print("\n--- Current Crew Availability ---")
    now = "2026-01-27T12:00:00"
    avail_rows = conn.execute(
        """
        SELECT c.name, ca.start_time, ca.end_time
        FROM crew_availability ca
        JOIN crew c ON ca.crew_id = c.id
        WHERE ca.start_time <= ? AND ca.end_time > ?
    """,
        (now, now),
    ).fetchall()
    for r in avail_rows:
        print(f"Name: {r['name']}, Start: {r['start_time']}, End: {r['end_time']}")

    print("\n--- P22P6 Status ---")
    app_rows = conn.execute(
        """
        SELECT a.name, aa.start_time, aa.end_time
        FROM appliance_availability aa
        JOIN appliance a ON aa.appliance_id = a.id
        WHERE a.name = 'P22P6' AND aa.start_time <= ? AND aa.end_time > ?
    """,
        (now, now),
    ).fetchall()
    for r in app_rows:
        print(f"Appliance: {r['name']}, Start: {r['start_time']}, End: {r['end_time']}")

    conn.close()


if __name__ == "__main__":
    check()
