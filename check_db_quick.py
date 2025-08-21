#!/usr/bin/env python3
"""Quick database check script."""

import sqlite3

from config import config

conn = sqlite3.connect(config.db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Database Contents ===")
cursor.execute("SELECT COUNT(*) as count FROM crew")
crew_count = cursor.fetchone()["count"]
print(f"Crew members: {crew_count}")

cursor.execute("SELECT COUNT(*) as count FROM appliance")
appliance_count = cursor.fetchone()["count"]
print(f"Appliances: {appliance_count}")

cursor.execute("SELECT COUNT(*) as count FROM crew_availability")
crew_avail_count = cursor.fetchone()["count"]
print(f"Crew availability entries: {crew_avail_count}")

cursor.execute("SELECT COUNT(*) as count FROM appliance_availability")
app_avail_count = cursor.fetchone()["count"]
print(f"Appliance availability entries: {app_avail_count}")

print("\n=== Sample Crew Data ===")
cursor.execute("SELECT * FROM crew LIMIT 3")
for row in cursor.fetchall():
    role = row["role"] if "role" in row.keys() and row["role"] else "N/A"
    print(f'ID: {row["id"]}, Name: {row["name"]}, Role: {role}')

conn.close()
