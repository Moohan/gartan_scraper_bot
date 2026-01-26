import sqlite3

conn = sqlite3.connect("gartan_availability.db")
cursor = conn.cursor()
cursor.execute("SELECT id, name FROM crew WHERE name LIKE '%HAYES%'")
print(cursor.fetchall())
conn.close()
