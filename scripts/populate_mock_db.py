import os
import sqlite3
from datetime import datetime, timedelta

from config import config
from db_store import init_db, insert_crew_availability, insert_crew_details


def populate_mock_data():
    db_path = config.db_path
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = init_db(db_path, reset=True)

    crew_list = []
    for i in range(50):
        crew_list.append(
            {
                "name": f"Crew Member {i}",
                "role": "FFC" if i % 5 == 0 else "FFD",
                "contract_hours": "42.0 hrs",
                "skills": "TTR LGV BA",
            }
        )

    insert_crew_details(crew_list, db_conn=conn)

    now = datetime.now()
    availability_data = []
    for i in range(50):
        slots = {}
        # Make them available for today
        for hour in range(0, 24):
            slots[f"{now.strftime('%d/%m/%Y')} {hour:02d}00"] = True

        availability_data.append({"name": f"Crew Member {i}", "availability": slots})

    insert_crew_availability(availability_data, db_conn=conn)

    # Add an appliance
    cursor = conn.cursor()
    cursor.execute("INSERT INTO appliance (name) VALUES ('P22P6')")
    cursor.execute("SELECT id FROM appliance WHERE name = 'P22P6'")
    app_id = cursor.fetchone()[0]

    # Appliance availability
    cursor.execute(
        "INSERT INTO appliance_availability (appliance_id, start_time, end_time) VALUES (?, ?, ?)",
        (
            app_id,
            now.replace(hour=0, minute=0, second=0, microsecond=0),
            now.replace(hour=23, minute=59, second=59, microsecond=0),
        ),
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    populate_mock_data()
