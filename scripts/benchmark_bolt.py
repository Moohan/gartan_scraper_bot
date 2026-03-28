import time
import sqlite3
import os
from datetime import datetime, timedelta
from api_server import app
import api_server

def setup_test_db(db_path, num_crew=100):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, skills TEXT, contract_hours TEXT)")
    c.execute("CREATE TABLE crew_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)")
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    c.execute("CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, appliance_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)")

    crew_data = []
    for i in range(num_crew):
        crew_data.append((f"Crew {i:03d}", "FFC", "BA LGV TTR", "42"))

    c.executemany("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", crew_data)

    now = datetime.now()
    future = now + timedelta(hours=8)

    avail_data = []
    for i in range(1, num_crew + 1):
        avail_data.append((i, now.isoformat(), future.isoformat()))

    c.executemany("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)", avail_data)

    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)", (now.isoformat(), future.isoformat()))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    DB_PATH = "benchmark.db"
    api_server.DB_PATH = DB_PATH
    setup_test_db(DB_PATH, 100)

    app.config["TESTING"] = True
    client = app.test_client()

    # Warmup
    client.get("/")

    print("Benchmarking 100 requests to / ...")
    start = time.time()
    for _ in range(100):
        client.get("/")
    end = time.time()

    avg_time = (end - start) / 100
    print(f"Average time for 100 requests: {avg_time:.4f}s")

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
