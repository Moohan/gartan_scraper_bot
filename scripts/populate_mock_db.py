import random
import sqlite3
from datetime import datetime, timedelta

from config import config

DB_PATH = config.db_path


def populate_mock_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Clear existing data
    c.execute("DROP TABLE IF EXISTS crew_availability")
    c.execute("DROP TABLE IF EXISTS appliance_availability")
    c.execute("DROP TABLE IF EXISTS crew")
    c.execute("DROP TABLE IF EXISTS appliance")

    # Recreate tables
    c.execute("""
    CREATE TABLE crew (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        role TEXT,
        skills TEXT,
        contract_hours TEXT
    );
    """)
    c.execute("""
    CREATE TABLE appliance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    """)
    c.execute("""
    CREATE TABLE crew_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crew_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        FOREIGN KEY (crew_id) REFERENCES crew(id)
    );
    """)
    c.execute("""
    CREATE TABLE appliance_availability (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appliance_id INTEGER NOT NULL,
        start_time DATETIME NOT NULL,
        end_time DATETIME NOT NULL,
        FOREIGN KEY (appliance_id) REFERENCES appliance(id)
    );
    """)

    # Add crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    skills_list = ["TTR", "LGV", "BA", "ERD", "IC"]

    crew_data = []
    for i in range(50):
        name = f"Crew Member {i+1}"
        role = random.choice(roles)
        skills = " ".join(random.sample(skills_list, k=random.randint(1, 3)))
        contract = f"{random.randint(10, 40)} hours"
        crew_data.append((name, role, skills, contract))

    c.executemany(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
        crew_data,
    )

    # Add appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    appliance_id = c.lastrowid

    # Add availability
    now = datetime.now()
    start_of_week = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Each crew member is available for most of the week
    avail_data = []
    for crew_id in range(1, 51):
        # Current availability
        avail_data.append((crew_id, now - timedelta(hours=2), now + timedelta(hours=6)))
        # Other blocks in the week
        for d in range(7):
            day = start_of_week + timedelta(days=d)
            avail_data.append(
                (crew_id, day + timedelta(hours=8), day + timedelta(hours=18))
            )

    c.executemany(
        "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
        avail_data,
    )

    # Appliance availability
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
        (appliance_id, now - timedelta(hours=24), now + timedelta(hours=24)),
    )

    conn.commit()
    conn.close()
    print("Populated 50 crew members and their availability.")


if __name__ == "__main__":
    populate_mock_data()
