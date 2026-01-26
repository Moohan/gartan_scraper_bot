import json
import sqlite3
from datetime import datetime

conn = sqlite3.connect("gartan_availability.db")
cursor = conn.cursor()

# Check specific crew member 4540 (HAYES, JA)
print("--- Database Check ---")
cursor.execute("""
    SELECT c.name, ca.start_time, ca.end_time
    FROM crew c
    JOIN crew_availability ca ON c.id = ca.crew_id
    WHERE c.id = 4540
    AND ca.start_time <= datetime('now')
    AND ca.end_time >= datetime('now')
""")
current = cursor.fetchone()

if current:
    print(f"Current Status: Available")
    print(f"Block: {current[1]} to {current[2]}")
else:
    print("Current Status: Not Available (No active block found)")

# Check future blocks
cursor.execute("""
    SELECT start_time, end_time
    FROM crew_availability
    WHERE crew_id = 4540
    AND start_time > datetime('now')
    ORDER BY start_time ASC
""")
future = cursor.fetchall()
print(f"Future Blocks: {future}")

conn.close()
