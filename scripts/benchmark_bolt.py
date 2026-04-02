import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta

import api_server
from api_server import DB_PATH, app


def setup_benchmark_db(num_crew=50):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
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

    now = datetime.now()
    future = now + timedelta(hours=8)

    for i in range(num_crew):
        name = f"CREW_{i}"
        role = "FFC" if i % 5 == 0 else "FFD"
        skills = "BA TTR LGV" if i % 10 == 0 else "BA"
        c.execute(
            "INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
            (name, role, skills, "42"),
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
    return path


def run_benchmark(db_path, iterations=20):
    api_server.DB_PATH = db_path
    app.config["TESTING"] = True
    client = app.test_client()

    # Warmup
    with app.app_context():
        client.get("/")

    start_time = time.time()
    for _ in range(iterations):
        with app.app_context():
            client.get("/")
    end_time = time.time()

    avg_latency = (end_time - start_time) / iterations
    print(
        f"Average latency over {iterations} requests with {db_path}: {avg_latency:.4f}s"
    )
    return avg_latency


if __name__ == "__main__":
    db_path = setup_benchmark_db(100)
    try:
        run_benchmark(db_path)
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
