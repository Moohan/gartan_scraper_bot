import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta

import api_server
from api_server import app


def setup_benchmark_db():
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    api_server.DB_PATH = temp_path

    conn = sqlite3.connect(temp_path)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, skills TEXT, contract_hours TEXT)"
    )
    c.execute(
        "CREATE TABLE crew_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)"
    )
    c.execute(
        "CREATE TABLE appliance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)"
    )
    c.execute(
        "CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, appliance_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)"
    )

    # Insert 50 crew members
    now = datetime.now()
    future = now + timedelta(hours=8)

    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    for i in range(50):
        name = f"CREW_{i}"
        role = roles[i % len(roles)]
        skills = "BA LGV TTR"
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            (name, role, skills, "42h"),
        )
        crew_id = c.lastrowid
        # Make half available
        if i % 2 == 0:
            c.execute(
                "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                (crew_id, now, future),
            )

    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    app_id = c.lastrowid
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
        (app_id, now, future),
    )

    conn.commit()
    conn.close()
    return temp_path


def run_benchmark():
    db_path = setup_benchmark_db()
    app.config["TESTING"] = True
    client = app.test_client()

    # Warm up
    client.get("/")

    iterations = 100
    start_time = time.time()
    for _ in range(iterations):
        client.get("/")
    end_time = time.time()

    avg_latency = (end_time - start_time) / iterations * 1000
    print(f"Average latency over {iterations} requests: {avg_latency:.2f} ms")

    os.unlink(db_path)


if __name__ == "__main__":
    run_benchmark()
