
import sqlite3
import random
from datetime import datetime, timedelta
from config import config
from db_store import init_db

def populate():
    print("Populating mock data...")
    init_db(reset=True)
    conn = sqlite3.connect(config.db_path)
    c = conn.cursor()

    # Create crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    skills_pool = ["TTR", "LGV", "BA", "ERD", "IC"]

    crew_data = []
    for i in range(50):
        name = f"Crew Member {i}"
        role = random.choice(roles)
        # Randomly assign 1-3 skills
        skills = " ".join(random.sample(skills_pool, k=random.randint(1, 3)))
        contract = f"{random.randint(10, 40)} hours"
        crew_data.append((name, role, skills, contract))

    c.executemany("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", crew_data)

    # Create appliances
    c.execute("INSERT INTO appliance (name) VALUES (?)", ("P22P6",))
    c.execute("INSERT INTO appliance (name) VALUES (?)", ("P22M1",))

    # Create availability
    now = datetime.now()
    start_time = now - timedelta(hours=2)
    end_time = now + timedelta(hours=6)

    # Make some crew available now
    c.execute("SELECT id FROM crew")
    crew_ids = [r[0] for r in c.fetchall()]

    avail_data = []
    for cid in crew_ids:
        if random.random() < 0.7: # 70% chance of being available
            avail_data.append((cid, start_time.isoformat(), end_time.isoformat()))

    c.executemany("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)", avail_data)

    # Make appliances available
    c.execute("SELECT id FROM appliance")
    app_ids = [r[0] for r in c.fetchall()]
    for aid in app_ids:
        c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
                  (aid, start_time.isoformat(), end_time.isoformat()))

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    populate()
