import os
import sqlite3
from datetime import datetime, timedelta

from api_server import DB_PATH, app
from db_store import init_db


def setup_mock_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    init_db(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES ('Test Officer', 'WC', 'BA TTR', '42h')"
    )
    c.execute(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES ('Test Driver', 'FFD', 'BA LGV', '42h')"
    )
    c.execute(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES ('Test FF1', 'FF', 'BA', '42h')"
    )
    c.execute(
        "INSERT INTO crew (name, role, skills, contract_hours) VALUES ('Test FF2', 'FF', 'BA', '42h')"
    )

    now = datetime.now()
    # All available
    for i in range(1, 5):
        c.execute(
            "INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)",
            (i, now - timedelta(hours=1), now + timedelta(hours=5)),
        )

    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (1, ?, ?)",
        (now - timedelta(hours=1), now + timedelta(hours=5)),
    )
    conn.commit()
    conn.close()


def verify_dashboard():
    client = app.test_client()
    res = client.get("/")
    assert res.status_code == 200
    html = res.data.decode()
    assert "Test Officer" in html
    assert "Test Driver" in html
    assert "OPERATIONAL" in html
    print("Dashboard verification successful!")


if __name__ == "__main__":
    setup_mock_db()
    verify_dashboard()
