
import time
import sqlite3
import os
from datetime import datetime, timedelta
from api_server import app, get_db

def setup_benchmark_db(num_crew=100):
    db_path = 'benchmark.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY, name TEXT, role TEXT, skills TEXT, contract_hours TEXT)")
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("CREATE TABLE crew_availability (id INTEGER PRIMARY KEY, crew_id INTEGER, start_time DATETIME, end_time DATETIME)")
    c.execute("CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY, appliance_id INTEGER, start_time DATETIME, end_time DATETIME)")

    # Insert crew members
    roles = ['WC', 'CM', 'CC', 'FFC', 'FFD', 'FFT']
    crew_data = []
    for i in range(num_crew):
        crew_data.append((i, f'Crew {i:04d}', roles[i % len(roles)], 'BA TTR LGV', '42.0 hours'))
    c.executemany("INSERT INTO crew VALUES (?, ?, ?, ?, ?)", crew_data)

    # Insert availability for all crew members (currently available)
    now = datetime.now()
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=4)
    avail_data = []
    for i in range(num_crew):
        avail_data.append((i, i, start_time, end_time))
    c.executemany("INSERT INTO crew_availability VALUES (?, ?, ?, ?)", avail_data)

    # Insert appliance
    c.execute("INSERT INTO appliance VALUES (1, 'P22P6')")
    c.execute("INSERT INTO appliance_availability VALUES (1, 1, ?, ?)", (start_time, end_time))

    conn.commit()
    conn.close()
    return db_path

def benchmark(num_crew=100):
    db_path = setup_benchmark_db(num_crew)

    # Patching config for benchmark
    import config
    original_db_path = config.config.db_path
    config.config.db_path = db_path

    client = app.test_client()

    # Warm up
    client.get('/')

    start = time.time()
    iterations = 50
    for _ in range(iterations):
        client.get('/')
    end = time.time()

    avg_latency = (end - start) / iterations
    print(f"Average latency for / with {num_crew} crew: {avg_latency:.4f}s")

    # Restore config
    config.config.db_path = original_db_path
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    benchmark(100)
    benchmark(500)
