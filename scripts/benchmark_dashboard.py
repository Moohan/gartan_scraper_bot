import os
import sqlite3
import time
from datetime import datetime, timedelta

from api_server import app, get_db
from db_store import init_db


def setup_test_data(num_crew=50):
    with app.app_context():
        init_db(reset=True)
        conn = get_db()
        # Insert crew
        crew_data = []
        for i in range(num_crew):
            crew_data.append((f"Crew Member {i}", "FFC", "TTR LGV BA", "42h"))
        conn.executemany(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            crew_data,
        )

        # Get IDs
        crew_ids = [row[0] for row in conn.execute("SELECT id FROM crew").fetchall()]

        # Insert availability
        now = datetime.now()
        avail_data = []
        for cid in crew_ids:
            # Add two overlapping blocks for each crew member to test duplicate handling
            # Block 1: 2h ago to 2h from now
            avail_data.append((cid, now - timedelta(hours=2), now + timedelta(hours=2)))
            # Block 2: 1h ago to 4h from now (longer, overlapping)
            avail_data.append((cid, now - timedelta(hours=1), now + timedelta(hours=4)))
        conn.executemany(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            avail_data,
        )

        # Insert appliance
        conn.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
        aid = conn.execute("SELECT id FROM appliance WHERE name='P22P6'").fetchone()[0]
        conn.execute(
            "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
            (aid, now - timedelta(hours=2), now + timedelta(hours=2)),
        )
        conn.commit()


def benchmark(num_requests=100):
    client = app.test_client()

    # Warmup
    client.get("/")

    start_time = time.time()
    for _ in range(num_requests):
        resp = client.get("/")
        # Check for duplicates in response HTML (basic check)
        # We expect only one card for 'Crew Member 0'
        html = resp.get_data(as_text=True)
        count = html.count("Crew Member 0")
        if count != 1:
            raise ValueError(
                f"Duplicate crew member detected in response! Found {count} instances."
            )

    end_time = time.time()

    avg_time = (end_time - start_time) / num_requests
    print(f"Average time per request: {avg_time:.4f}s")
    print("Verification passed: No duplicates found.")
    return avg_time


if __name__ == "__main__":
    setup_test_data(50)
    benchmark(50)
