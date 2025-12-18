import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, ".")
import api_server
from api_server import get_appliance_duration_data, get_crew_duration_data


def setup_temp_db():
    fd, temp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    api_server.DB_PATH = temp_path
    conn = sqlite3.connect(temp_path)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)"
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
    conn.commit()
    return conn, temp_path


def teardown_temp_db(conn, path):
    conn.close()
    try:
        os.unlink(path)
    except PermissionError:
        pass


def test_crew_duration_string_and_null():
    conn, path = setup_temp_db()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO crew (id,name) VALUES (1,'TEST CREW')")
        now = datetime.now()
        start = (now - timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        end = (now + timedelta(minutes=60)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO crew_availability (crew_id,start_time,end_time) VALUES (?,?,?)",
            (1, start, end),
        )
        conn.commit()
        result = get_crew_duration_data(1)
        assert "duration" in result
        # Valid states: None (not available) or hours string ending 'h'
        if result["duration"] is not None:
            assert result["duration"].endswith("h")
        result2 = get_crew_duration_data(999)
        assert "error" in result2
    finally:
        teardown_temp_db(conn, path)


def test_appliance_duration_string_and_null():
    conn, path = setup_temp_db()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO appliance (id,name) VALUES (1,'P22P6')")
        now = datetime.now()
        start = (now - timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        end = (now + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO appliance_availability (appliance_id,start_time,end_time) VALUES (?,?,?)",
            (1, start, end),
        )
        conn.commit()
        result = get_appliance_duration_data("P22P6")
        assert "duration" in result
        if result["duration"] is not None:
            assert result["duration"].endswith("h")
        result2 = get_appliance_duration_data("UNKNOWN")
        assert "error" in result2
    finally:
        teardown_temp_db(conn, path)
