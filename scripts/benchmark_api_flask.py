import time
from api_server import app, get_db
import sqlite3
from datetime import datetime, timedelta
from db_store import init_db

def setup_dummy_data():
    init_db()
    # Ensure there is some data in the DB for benchmarking
    with app.app_context():
        with get_db() as conn:
            # Clear existing data if necessary or just add more
            # For simplicity, let's assume there is some data.
            # If not, let's add 50 crew members.
            count = conn.execute("SELECT COUNT(*) FROM crew").fetchone()[0]
            if count < 50:
                print(f"Adding {50 - count} dummy crew members...")
                for i in range(50 - count):
                    conn.execute(
                        "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                        (f"Crew {i+count}", "FFD", "BA LGV", "42 hours")
                    )
                conn.commit()

            # Add availability for now
            now = datetime.now()
            crew_ids = [r[0] for r in conn.execute("SELECT id FROM crew").fetchall()]
            for cid in crew_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                    (cid, now - timedelta(hours=1), now + timedelta(hours=1))
                )
            conn.commit()

def benchmark_root(iterations=20):
    client = app.test_client()
    latencies = []
    # Warm up
    client.get('/')

    for _ in range(iterations):
        start = time.perf_counter()
        client.get('/')
        latencies.append(time.perf_counter() - start)

    avg = sum(latencies) / len(latencies)
    print(f"Dashboard (/) benchmark with {len(latencies)} iterations:")
    print(f"Average latency: {avg:.4f}s")
    print(f"Min latency: {min(latencies):.4f}s")
    print(f"Max latency: {max(latencies):.4f}s")

if __name__ == "__main__":
    setup_dummy_data()
    benchmark_root()
