import os
import sqlite3
from datetime import datetime, timedelta

from config import config
from db_store import init_db


def populate():
    db_path = config.db_path
    if os.path.exists(db_path):
        os.remove(db_path)

    # Ensure directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = init_db(db_path)
    c = conn.cursor()

    # Add an appliance
    c.execute("INSERT INTO appliance (name) VALUES (?)", ("P22P6",))
    appliance_id = c.lastrowid

    now = datetime.now()
    # Appliance availability
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
        (appliance_id, now - timedelta(hours=1), now + timedelta(hours=10)),
    )

    # Add 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    skills_pool = ["TTR", "LGV", "BA", "ERD", "IC"]

    for i in range(50):
        name = f"Crew Member {i}"
        role = roles[i % len(roles)]
        # Mix of skills
        skills = " ".join([s for j, s in enumerate(skills_pool) if (i + j) % 3 == 0])
        contract_hours = f"{30 + (i % 10)} hours"

        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            (name, role, skills, contract_hours),
        )
        crew_id = c.lastrowid

        # Availability: half of them available now
        if i % 2 == 0:
            c.execute(
                "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                (crew_id, now - timedelta(hours=1), now + timedelta(hours=5)),
            )

        # Some random other availability blocks
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (crew_id, now + timedelta(days=1), now + timedelta(days=1, hours=8)),
        )

    conn.commit()
    conn.close()
    print("Database populated with 50 crew members.")


if __name__ == "__main__":
    populate()
