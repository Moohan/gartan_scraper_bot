
import time
import sqlite3
import os
from datetime import datetime, timedelta
from api_server import app, get_db, DB_PATH
from db_store import init_db

def setup_mock_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = init_db(DB_PATH)
    c = conn.cursor()

    # Insert 50 crew members
    crew_data = []
    for i in range(50):
        name = f"Crew Member {i}"
        role = ["WC", "CM", "CC", "FFC", "FFD", "FFT"][i % 6]
        skills = "BA"
        if i % 3 == 0: skills += " LGV"
        if i % 4 == 0: skills += " TTR"
        contract = "42 hours"
        crew_data.append((name, role, skills, contract))

    c.executemany("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", crew_data)

    # Set half of them as available now
    now = datetime.now()
    availability_data = []
    for i in range(25):
        crew_id = i + 1
        start_time = now - timedelta(hours=2)
        end_time = now + timedelta(hours=6)
        availability_data.append((crew_id, start_time, end_time))

    c.executemany("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)", availability_data)

    # Appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
              (now - timedelta(hours=2), now + timedelta(hours=6)))

    conn.commit()
    conn.close()

def benchmark_root():
    client = app.test_client()

    # Warm up
    client.get("/")

    start = time.perf_counter()
    for _ in range(10):
        client.get("/")
    end = time.perf_counter()

    avg_time = (end - start) / 10
    print(f"Average time for /: {avg_time:.4f}s")

if __name__ == "__main__":
    setup_mock_db()
    benchmark_root()
