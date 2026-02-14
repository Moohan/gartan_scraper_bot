
import sqlite3
from datetime import datetime, timedelta
from db_store import init_db
from config import config

def populate():
    db_path = config.db_path
    print(f"Populating database at {db_path}")
    conn = init_db(db_path, reset=True)
    c = conn.cursor()

    # Add crew
    crew_members = [
        (f"Crew Member {i}", "FFD", "BA TTR LGV", "42 hours") for i in range(1, 51)
    ]
    c.executemany("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", crew_members)

    # Add appliances
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute("INSERT INTO appliance (name) VALUES ('P22P7')")

    # Add availability for all crew for the next 24 hours
    now = datetime.now()
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=23)

    c.execute("SELECT id FROM crew")
    crew_ids = [row[0] for row in c.fetchall()]

    availability = [(cid, start, end) for cid in crew_ids]
    c.executemany("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)", availability)

    # Add appliance availability
    c.execute("SELECT id FROM appliance WHERE name = 'P22P6'")
    p22p6_id = c.fetchone()[0]
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)", (p22p6_id, start, end))

    conn.commit()
    conn.close()
    print("Mock database populated with 50 crew members.")

if __name__ == "__main__":
    populate()
