import sqlite3
from datetime import datetime

conn = sqlite3.connect('gartan_availability.db')
cursor = conn.cursor()

# Get recent/future availability
query = """
SELECT c.name, ca.start_time, ca.end_time
FROM crew c
JOIN crew_availability ca ON c.id = ca.crew_id
WHERE ca.end_time > date('now')
ORDER BY ca.start_time ASC
LIMIT 10
"""

results = cursor.execute(query).fetchall()
print("Found availability blocks:")
for row in results:
    print(f"Name: {row[0]}, Start: {row[1]}, End: {row[2]}")

conn.close()
