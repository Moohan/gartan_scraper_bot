
import time
import sqlite3
from datetime import datetime, timedelta
from api_server import app, get_db

def setup_benchmark_db():
    db_path = "benchmark.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS crew")
    c.execute("DROP TABLE IF EXISTS crew_availability")
    c.execute("DROP TABLE IF EXISTS appliance")
    c.execute("DROP TABLE IF EXISTS appliance_availability")

    c.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY, name TEXT, role TEXT, skills TEXT, contract_hours TEXT)")
    c.execute("CREATE TABLE crew_availability (id INTEGER PRIMARY KEY, crew_id INTEGER, start_time DATETIME, end_time DATETIME)")
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY, appliance_id INTEGER, start_time DATETIME, end_time DATETIME)")

    # Insert 100 crew members
    now = datetime.now()
    for i in range(100):
        c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                  (f"Crew {i}", "FFD", "BA TTR", "42h"))
        crew_id = c.lastrowid
        # Half are available
        if i % 2 == 0:
            c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                      (crew_id, now - timedelta(hours=1), now + timedelta(hours=4)))

    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    app_id = c.lastrowid
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
              (app_id, now - timedelta(hours=1), now + timedelta(hours=4)))

    conn.commit()
    conn.close()
    return db_path

def run_benchmark():
    db_path = setup_benchmark_db()
    app.config['TESTING'] = True
    # We need to override the DB_PATH in api_server.py
    import api_server
    api_server.DB_PATH = db_path

    client = app.test_client()

    # Warm up
    client.get('/')

    start_time = time.time()
    iterations = 50
    for _ in range(iterations):
        client.get('/')
    end_time = time.time()

    avg_latency = (end_time - start_time) / iterations
    print(f"Average latency over {iterations} requests: {avg_latency:.4f}s")

if __name__ == "__main__":
    run_benchmark()
