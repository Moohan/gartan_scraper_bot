
import sqlite3
import os
from datetime import datetime, timedelta
from db_store import init_db
from config import config

DB_PATH = config.db_path

def populate():
    # Ensure directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = init_db(DB_PATH)
    c = conn.cursor()

    # Add 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    skills_pool = ["TTR", "LGV", "BA", "IC", "ERD"]

    crew_data = []
    for i in range(1, 51):
        name = f"Crew Member {i}"
        role = roles[i % len(roles)]
        # Mix skills
        skills = []
        if i % 2 == 0: skills.append("BA")
        if i % 3 == 0: skills.append("LGV")
        if i % 4 == 0: skills.append("TTR")
        if i % 5 == 0: skills.append("IC")

        crew_data.append((name, role, " ".join(skills), "42 hours"))

    c.executemany("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", crew_data)

    # Add availability for some crew members
    # Make 20 crew members available now
    now = datetime.now()
    start = now - timedelta(hours=2)
    end = now + timedelta(hours=6)

    avail_data = []
    for i in range(1, 21):
        avail_data.append((i, start, end))

    c.executemany("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)", avail_data)

    # Add appliance P22P6
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)", (start, end))

    conn.commit()
    conn.close()
    print(f"Populated {DB_PATH} with 50 crew members and 20 available.")

if __name__ == "__main__":
    populate()
