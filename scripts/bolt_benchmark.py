import time
import json
import sqlite3
import os
from api_server import app, init_db

def setup_benchmark_db():
    db_path = 'benchmark.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    app.config['DATABASE'] = db_path
    with app.app_context():
        init_db()
        db = sqlite3.connect(db_path)
        cursor = db.cursor()

        # Add 50 crew members
        for i in range(50):
            cursor.execute(
                "INSERT INTO crew (name, role, skills, contract) VALUES (?, ?, ?, ?)",
                (f"Crew Member {i}", "FFD", "BA LGV TTR", 42)
            )
            crew_id = cursor.lastrowid

            # Make half of them available
            if i % 2 == 0:
                cursor.execute(
                    "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, datetime('now'), datetime('now', '+8 hours'))",
                    (crew_id,)
                )
        db.commit()
        db.close()
    return db_path

def run_benchmark(iterations=100):
    db_path = setup_benchmark_db()
    client = app.test_client()

    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        response = client.get('/')
        end = time.perf_counter()
        assert response.status_code == 200
        times.append((end - start) * 1000)

    avg_time = sum(times) / len(times)
    print(f"Average response time over {iterations} iterations: {avg_time:.2f}ms")

    if os.path.exists(db_path):
        os.remove(db_path)

    return avg_time

if __name__ == "__main__":
    run_benchmark()
