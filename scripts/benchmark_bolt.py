import time
import os
import sqlite3
from datetime import datetime, timedelta
from api_server import app, get_db

def setup_dummy_data(num_crew=50):
    with app.app_context():
        conn = get_db()
        conn.execute("DELETE FROM crew_availability")
        conn.execute("DELETE FROM crew")

        now = datetime.now()
        for i in range(num_crew):
            name = f"Crew {i}"
            conn.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                         (name, "FFD", "BA", "40 hours"))
            crew_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            # Available for next 4 hours
            conn.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                         (crew_id, now - timedelta(hours=1), now + timedelta(hours=3)))
        conn.commit()

def benchmark_root():
    client = app.test_client()

    # Warm up
    client.get("/")

    start_time = time.time()
    num_requests = 20
    for _ in range(num_requests):
        client.get("/")
    end_time = time.time()

    avg_time = (end_time - start_time) / num_requests
    print(f"Average time for /: {avg_time:.4f}s")
    return avg_time

if __name__ == "__main__":
    # Ensure DB is initialized
    from db_store import init_db
    init_db()

    setup_dummy_data(50)
    benchmark_root()
