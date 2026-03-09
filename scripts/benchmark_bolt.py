import time
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta
from api_server import app
import api_server

def setup_benchmark_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY, name TEXT, role TEXT, skills TEXT, contract_hours TEXT)")
    c.execute("CREATE TABLE crew_availability (id INTEGER PRIMARY KEY, crew_id INTEGER, start_time DATETIME, end_time DATETIME)")
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY, appliance_id INTEGER, start_time DATETIME, end_time DATETIME)")

    # Insert 50 crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    now = datetime.now()
    future = now + timedelta(hours=8)

    crew_data = []
    avail_data = []
    for i in range(1, 51):
        role = roles[i % len(roles)]
        name = f"CREW_{i}"
        crew_data.append((i, name, role, "BA LGV TTR", "42"))
        # Make everyone available
        avail_data.append((i, i, now.isoformat(), future.isoformat()))

    c.executemany("INSERT INTO crew VALUES (?, ?, ?, ?, ?)", crew_data)
    c.executemany("INSERT INTO crew_availability VALUES (?, ?, ?, ?)", avail_data)

    c.execute("INSERT INTO appliance VALUES (1, 'P22P6')")
    c.execute("INSERT INTO appliance_availability VALUES (1, 1, ?, ?)", (now.isoformat(), future.isoformat()))

    conn.commit()
    conn.close()
    return path

def run_benchmark(db_path, iterations=100):
    api_server.DB_PATH = db_path
    app.config['TESTING'] = True
    client = app.test_client()

    # Warm up
    client.get("/")

    start_time = time.time()
    for _ in range(iterations):
        client.get("/")
    end_time = time.time()

    avg_time = (end_time - start_time) / iterations * 1000
    print(f"Average response time over {iterations} iterations: {avg_time:.2f}ms")
    return avg_time

if __name__ == "__main__":
    db_path = setup_benchmark_db()
    try:
        run_benchmark(db_path)
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
