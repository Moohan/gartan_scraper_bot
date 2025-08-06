#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect("gartan_availability.db")
cursor = conn.cursor()

cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
results = cursor.fetchall()

print("Database Schema:")
print("================")
for row in results:
    if row[0]:
        print(row[0])
        print()

conn.close()
