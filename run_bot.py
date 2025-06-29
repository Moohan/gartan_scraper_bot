from gartan_fetch import (
    gartan_login_and_get_session,
    fetch_grid_html_for_date,
)
from parse_grid import parse_grid_html
import json
from datetime import datetime

if __name__ == "__main__":
    from datetime import timedelta

    # Get today and the next 3 days
    today = datetime.now()
    days = [today + timedelta(days=i) for i in range(4)]
    date_strs = [d.strftime("%d/%m/%Y") for d in days]

    # Log in once and reuse the session
    session = gartan_login_and_get_session()
    crew_dict = {}
    all_slots = []
    for booking_date in date_strs:
        print(f"Fetching availability for {booking_date}...")
        grid_html = fetch_grid_html_for_date(session, booking_date)
        if not grid_html:
            print(f"Failed to fetch grid HTML for {booking_date}.")
            continue
        result = parse_grid_html(grid_html, date=booking_date)
        crew_list = result.get("crew_availability", [])
        for crew in crew_list:
            name = crew["name"]
            if name not in crew_dict:
                crew_dict[name] = {"name": name, "availability": {}, "_all_slots": []}
            # Merge availability
            for slot, avail in crew["availability"].items():
                crew_dict[name]["availability"][slot] = avail
                crew_dict[name]["_all_slots"].append((slot, avail))
    # Compute next_available for each crew member
    from datetime import datetime as dt

    now = dt.now()
    for crew in crew_dict.values():
        # Sort slots chronologically
        slot_tuples = []
        for slot, avail in crew["_all_slots"]:
            try:
                slot_dt = dt.strptime(slot, "%d/%m/%Y %H%M")
                slot_tuples.append((slot_dt, avail))
            except Exception:
                continue
        slot_tuples.sort()
        next_avail = None
        for slot_dt, avail in slot_tuples:
            if slot_dt >= now and avail:
                if slot_dt <= now:
                    next_avail = "now"
                else:
                    next_avail = slot_dt.strftime("%d/%m/%Y %H:%M")
                break
        crew["next_available"] = next_avail
        del crew["_all_slots"]
    # Output as a list of crew
    crew_list = list(crew_dict.values())
    with open("gridAvail.json", "w", encoding="utf-8") as f:
        json.dump(crew_list, f, indent=2)
    print(
        f"Saved crew availability for {len(crew_list)} crew members to gridAvail.json"
    )
