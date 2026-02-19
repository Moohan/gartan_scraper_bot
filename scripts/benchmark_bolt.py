#!/usr/bin/env python3
"""Benchmark script for API server performance."""

import os
import sqlite3
import tempfile
import time
from datetime import datetime, timedelta

import sys
sys.path.insert(0, ".")

import api_server
from api_server import app

def setup_benchmark_db(num_crew=50):
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    api_server.DB_PATH = temp_path

    conn = sqlite3.connect(temp_path)
    c = conn.cursor()
    c.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, skills TEXT, contract_hours TEXT)")
    c.execute("CREATE TABLE crew_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)")
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    c.execute("CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, appliance_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL)")

    # Insert crew members
    roles = ["WC", "CM", "CC", "FFC", "FFD", "FFT"]
    for i in range(num_crew):
        role = roles[i % len(roles)]
        skills = "BA"
        if i % 3 == 0: skills += " LGV"
        if i % 4 == 0: skills += " TTR"

        c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)",
                  (f"CREW_{i}", role, skills, "42h"))

        crew_id = c.lastrowid
        # Half are available
        if i % 2 == 0:
            now = datetime.now()
            future = now + timedelta(hours=8)
            c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
                      (crew_id, now, future))

    # Insert appliance
    c.execute("INSERT INTO appliance (name) VALUES (?)", ("P22P6",))
    app_id = c.lastrowid
    now = datetime.now()
    future = now + timedelta(hours=8)
    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
              (app_id, now, future))

    conn.commit()
    conn.close()
    return temp_path

def run_benchmark(num_requests=20):
    app.config["TESTING"] = True
    client = app.test_client()

    # Warm up
    client.get("/")

    start_time = time.perf_counter()
    for _ in range(num_requests):
        client.get("/")
    end_time = time.perf_counter()

    avg_time = (end_time - start_time) / num_requests
    print(f"Average time for /: {avg_time*1000:.2f}ms")
    return avg_time

if __name__ == "__main__":
    db_path = setup_benchmark_db(50)
    try:
        run_benchmark()
    finally:
        os.unlink(db_path)
