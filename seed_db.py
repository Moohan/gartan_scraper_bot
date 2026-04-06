import sqlite3
from datetime import datetime, timedelta
from config import config

DB_PATH = config.db_path

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS crew_availability")
    c.execute("DROP TABLE IF EXISTS appliance_availability")
    c.execute("DROP TABLE IF EXISTS crew")
    c.execute("DROP TABLE IF EXISTS appliance")

    c.execute("CREATE TABLE crew (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, role TEXT, skills TEXT, contract_hours TEXT)")
    c.execute("CREATE TABLE appliance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE)")
    c.execute("CREATE TABLE crew_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, crew_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL, FOREIGN KEY (crew_id) REFERENCES crew(id))")
    c.execute("CREATE TABLE appliance_availability (id INTEGER PRIMARY KEY AUTOINCREMENT, appliance_id INTEGER NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL, FOREIGN KEY (appliance_id) REFERENCES appliance(id))")

    # Seed crew
    crew_list = [
        ('Alice Smith', 'WC', 'TTR LGV BA', '42'),
        ('Bob Jones', 'CM', 'LGV BA', '35'),
        ('Charlie Brown', 'FFC', 'BA', '42'),
        ('Diana Prince', 'FFD', 'BA', '35')
    ]
    for name, role, skills, hours in crew_list:
        c.execute("INSERT INTO crew (name, role, skills, contract_hours) VALUES (?, ?, ?, ?)", (name, role, skills, hours))

    # Seed appliance
    c.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    c.execute("SELECT id FROM appliance WHERE name='P22P6'")
    appliance_id = c.fetchone()[0]

    now = datetime.now()
    start = (now - timedelta(hours=1)).isoformat()
    end = (now + timedelta(hours=8)).isoformat()

    # All crew available
    c.execute("SELECT id FROM crew")
    crew_ids = [r[0] for r in c.fetchall()]
    for cid in crew_ids:
        c.execute("INSERT INTO crew_availability (crew_id, start_time, end_time) VALUES (?, ?, ?)", (cid, start, end))

    c.execute("INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)", (appliance_id, start, end))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
