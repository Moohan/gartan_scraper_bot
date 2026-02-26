import sqlite3
import sys
from datetime import datetime, timedelta

import pandas as pd


def main():
    excel_path = "ScottishfrsEmployeeAvailabilityReport.xlsx"
    db_path = "gartan_availability.db"
    crew_name = "HAYES, JA"
    end_date_limit = datetime.strptime("31/07/26", "%d/%m/%y").date()

    print(f"Loading Excel file: {excel_path}...")
    df = pd.read_excel(excel_path, skiprows=7)
    df = df.dropna(subset=["Name"])

    print(f"Connecting to database: {db_path}...")
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    c = conn.cursor()

    c.execute("SELECT id FROM crew WHERE name=?", (crew_name,))
    row = c.fetchone()
    if not row:
        print(f"Error: Crew member '{crew_name}' not found in database.")
        sys.exit(1)
    crew_id = row[0]

    c.execute(
        "SELECT start_time, end_time FROM crew_availability WHERE crew_id=?", (crew_id,)
    )
    db_blocks_raw = c.fetchall()

    # SQLite might return strings or datetime objects depending on adapter
    db_blocks = []
    for start, end in db_blocks_raw:
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        db_blocks.append((start, end))

    print(f"Found {len(db_blocks)} availability blocks in DB for {crew_name}.")

    def is_covered(slot_start, slot_end):
        for b_start, b_end in db_blocks:
            if b_start <= slot_start and b_end >= slot_end:
                return True
        return False

    excel_slots_count = 0
    db_covered_slots = 0
    discrepancies_excel_has_db_misses = []
    discrepancies_db_has_excel_misses = []

    slot_cols = [
        f"{str(h).zfill(2)}:{str(m).zfill(2)}"
        for h in range(24)
        for m in (0, 15, 30, 45)
    ]

    print(f"Comparing valid slots up to {end_date_limit}...")

    for idx, row in df.iterrows():
        name = row["Name"]
        if pd.isna(name) or str(name).strip() != crew_name:
            continue

        date_str = str(row["Date"])
        if not date_str or date_str == "nan":
            continue

        try:
            # e.g. "Sat 21/02/26" => "21/02/26"
            current_date_obj = datetime.strptime(
                date_str[4:].strip(), "%d/%m/%y"
            ).date()
        except ValueError:
            print(f"Skipping malformed date: {date_str}")
            continue

        if current_date_obj > end_date_limit:
            continue

        for col in slot_cols:
            if col not in df.columns:
                continue

            val = row[col]
            # In Gartan reports, an empty cell means Available.
            # Codes like 'O' (Off) or 'AL' (Annual Leave) mean Unavailable.
            is_excel_avail = pd.isna(val) or str(val).strip() == ""

            slot_start = datetime.combine(
                current_date_obj, datetime.strptime(col, "%H:%M").time()
            )
            slot_end = slot_start + timedelta(minutes=15)

            is_db_avail = is_covered(slot_start, slot_end)

            if is_excel_avail:
                excel_slots_count += 1
                if is_db_avail:
                    db_covered_slots += 1
                else:
                    discrepancies_excel_has_db_misses.append((slot_start, slot_end))
            else:
                if is_db_avail:
                    discrepancies_db_has_excel_misses.append((slot_start, slot_end))

    print("\n--- Validation Results ---")
    print(
        f"Total available slots in Excel (up to {end_date_limit}): {excel_slots_count}"
    )
    print(f"Total available slots in Excel fully covered by DB: {db_covered_slots}")
    print(
        f"False Negatives (Excel says YES, DB says NO): {len(discrepancies_excel_has_db_misses)}"
    )

    if len(discrepancies_excel_has_db_misses) > 0:
        for s, e in discrepancies_excel_has_db_misses[:10]:
            print(f"  Missed in DB: {s} to {e}")
        if len(discrepancies_excel_has_db_misses) > 10:
            print("  ... and more")

    print(
        f"False Positives (Excel says NO, DB says YES): {len(discrepancies_db_has_excel_misses)}"
    )
    if len(discrepancies_db_has_excel_misses) > 0:
        for s, e in discrepancies_db_has_excel_misses[:10]:
            print(f"  Phantom in DB: {s} to {e}")
        if len(discrepancies_db_has_excel_misses) > 10:
            print("  ... and more")

    if (
        len(discrepancies_excel_has_db_misses) == 0
        and len(discrepancies_db_has_excel_misses) == 0
    ):
        print("\nSUCCESS: Database perfectly matches the Excel report up to July 2026!")
    else:
        print("\nWARNING: Discrepancies found.")


if __name__ == "__main__":
    main()
