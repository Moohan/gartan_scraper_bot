
import sqlite3
from datetime import datetime, timedelta
from db_store import init_db, insert_crew_details, insert_crew_availability

def setup_benchmark_data():
    DB_PATH = "data/benchmark.db"
    init_db(DB_PATH, reset=True)
    conn = sqlite3.connect(DB_PATH)

    # Insert 50 crew members
    crew_list = []
    for i in range(50):
        crew_list.append({
            "name": f"Crew Member {i}",
            "role": ["WC", "CM", "CC", "FFC", "FFD", "FFT"][i % 6],
            "skills": "TTR LGV BA" if i % 2 == 0 else "BA",
            "contract_hours": "42.0 hours"
        })
    insert_crew_details(crew_list, db_conn=conn)

    # Insert availability for each
    now = datetime.now()
    start_time = now - timedelta(hours=1)
    end_time = now + timedelta(hours=4)

    # Format slots for _convert_slots_to_blocks
    slots = {
        start_time.strftime("%d/%m/%Y %H%M"): True,
        (start_time + timedelta(hours=1)).strftime("%d/%m/%Y %H%M"): True,
        (start_time + timedelta(hours=2)).strftime("%d/%m/%Y %H%M"): True,
        (start_time + timedelta(hours=3)).strftime("%d/%m/%Y %H%M"): True,
        (start_time + timedelta(hours=4)).strftime("%d/%m/%Y %H%M"): True,
    }

    crew_avail_list = []
    for i in range(50):
        crew_avail_list.append({
            "name": f"Crew Member {i}",
            "availability": slots
        })
    insert_crew_availability(crew_avail_list, db_conn=conn)
    conn.close()
    return DB_PATH

if __name__ == "__main__":
    path = setup_benchmark_data()
    print(f"Benchmark database created at {path}")
