import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv

from config import config
from db_store import (
    init_db,
    insert_appliance_availability,
    insert_crew_availability,
    insert_crew_details,
)
from gartan_fetch import fetch_grid_html_for_date, gartan_login_and_get_session
from parse_grid import parse_grid_html

load_dotenv()


def verify():
    print("Initializing DB...")
    # Use a test database or ensure the default one is clean for the test date
    import shutil

    if os.path.exists(config.db_path):
        print(f"Using existing DB: {config.db_path}")

    init_db()

    print("Attempting login...")
    session = gartan_login_and_get_session()
    if not session:
        print("Login failed")
        return

    date = "06/01/2026"
    print(f"Fetching HTML for {date}...")
    html = fetch_grid_html_for_date(session, date)
    if not html:
        print("Fetch failed")
        return

    # Save the grid HTML for debugging
    with open("grid_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved grid HTML to grid_debug.html")

    print(f"Parsing HTML (length: {len(html)})...")
    result = parse_grid_html(html, date)

    crew_list = result.get("crew_availability", [])
    appliance_dict = result.get("appliance_availability", {})

    print(f"Parsed {len(crew_list)} crew members and {len(appliance_dict)} appliances.")

    if crew_list:
        sample_crew = crew_list[0]
        print(f"Raw availability for {sample_crew['name']} (first 5 slots):")
        slots = list(sample_crew["availability"].keys())[:5]
        for slot in slots:
            print(f"  {slot}: {sample_crew['availability'][slot]}")

        # Check if any slot is True
        any_true = any(sample_crew["availability"].values())
        print(f"Any available slots for {sample_crew['name']}? {any_true}")

    if not crew_list and not appliance_dict:
        print("Parsing returned no data. Check HTML structure.")
        return

    print("Inserting data into DB...")
    conn = sqlite3.connect(config.db_path, detect_types=sqlite3.PARSE_DECLTYPES)

    # In db_store.py, insert_crew_availability depends on crew details existing
    insert_crew_details(crew_list, db_conn=conn)
    insert_crew_availability(crew_list, db_conn=conn)
    insert_appliance_availability(appliance_dict, db_conn=conn)

    conn.close()
    print("Insertion complete.")

    # Verification Query
    print("\n--- Verification Query ---")
    conn = sqlite3.connect(config.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM crew")
    print(f"Total crew in DB: {c.fetchone()[0]}")

    c.execute("SELECT COUNT(*) FROM crew_availability")
    print(f"Total crew availability blocks: {c.fetchone()[0]}")

    c.execute("SELECT COUNT(*) FROM appliance")
    print(f"Total appliances in DB: {c.fetchone()[0]}")

    c.execute("SELECT COUNT(*) FROM appliance_availability")
    print(f"Total appliance availability blocks: {c.fetchone()[0]}")

    # Sample data
    if crew_list:
        sample_name = crew_list[0]["name"]
        c.execute("SELECT id FROM crew WHERE name=?", (sample_name,))
        crew_id = c.fetchone()[0]
        c.execute(
            "SELECT start_time, end_time FROM crew_availability WHERE crew_id=? LIMIT 5",
            (crew_id,),
        )
        rows = c.fetchall()
        print(f"\nSample availability for {sample_name}:")
        for start, end in rows:
            print(f"  {start} to {end}")

    conn.close()


if __name__ == "__main__":
    verify()
