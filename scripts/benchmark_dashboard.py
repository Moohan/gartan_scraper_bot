import sqlite3
import time
import os
from datetime import datetime, timedelta
from config import config
from api_server import app
from db_store import init_db

def setup_mock_data(num_crew=50):
    db_path = config.db_path
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    # Use proper initialization
    conn = init_db(db_path=db_path, reset=True)
    c = conn.cursor()

    now = datetime.now()
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=8)

    for i in range(num_crew):
        c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                  (f"Crew Member {i}", "FF", "BA TTR LGV", "42 hours"))
        crew_id = c.lastrowid
        c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                  (crew_id, start, end))

    c.execute("INSERT INTO appliance (name) VALUES (?)", ("P22P6",))
    app_id = c.lastrowid
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
              (app_id, start, end))

    conn.commit()
    conn.close()
    print(f"Mock data setup complete in {db_path}")

def benchmark(iterations=20):
    client = app.test_client()

    print(f"Benchmarking dashboard with {iterations} iterations...")

    # Warm up
    client.get('/')

    start_time = time.time()
    for i in range(iterations):
        resp = client.get('/')
        if resp.status_code != 200:
            print(f"Error: got status {resp.status_code}")
            # print(resp.data)
            return
    end_time = time.time()

    total_time = end_time - start_time
    avg_time = total_time / iterations
    print(f"Total time for {iterations} requests: {total_time:.4f}s")
    print(f"Average request time: {avg_time:.4f}s")
    return avg_time

if __name__ == "__main__":
    setup_mock_data(100)
    benchmark()
