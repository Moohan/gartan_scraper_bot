import os
import sqlite3
from datetime import datetime, timedelta

from config import config
from db_store import init_db


def populate_mock_db():
    db_path = config.db_path
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = init_db(db_path, reset=True)
    c = conn.cursor()

    # Add crew members
    crew_data = []
    for i in range(1, 51):
        name = f"Crew Member {i}"
        role = ["WC", "CM", "CC", "FFC", "FFD", "FFT"][i % 6]
        skills = "BA TTR LGV" if i % 4 == 0 else "BA TTR" if i % 2 == 0 else "BA"
        contract_hours = "42.00 hrs"
        crew_data.append((name, role, skills, contract_hours))

    c.executemany(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
        crew_data,
    )

    # Add availability
    now = datetime.now()
    availability_data = []
    for i in range(1, 51):
        # 80% availability
        if i % 5 != 0:
            start_time = now - timedelta(hours=2)
            end_time = now + timedelta(hours=6)
            availability_data.append((i, start_time, end_time))

    c.executemany(
        "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
        availability_data,
    )

    # Add appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
        (now - timedelta(hours=2), now + timedelta(hours=10)),
    )

    conn.commit()
    conn.close()
    print(f"Mock database populated at {db_path} with 50 crew members.")


if __name__ == "__main__":
    populate_mock_db()
