from gartan_fetch import (
    gartan_login_and_get_session,
    fetch_grid_html_for_date,
    fetch_and_cache_grid_html,
)
from parse_grid import parse_grid_html, aggregate_crew_availability
import json
from datetime import datetime
import os
import time
import random

if __name__ == "__main__":
    from datetime import timedelta

    # Dynamically fetch days until all crew members' statuses are determined
    today = datetime.now()
    session = gartan_login_and_get_session()
    cache_dir = "_cache"
    os.makedirs(cache_dir, exist_ok=True)
    day_offset = 0
    all_statuses_determined = False
    max_days = 14
    daily_crew_lists = []
    crew_list_agg = []
    while not all_statuses_determined and day_offset < max_days:
        booking_date = (today + timedelta(days=day_offset)).strftime("%d/%m/%Y")
        # Pass day_offset to fetch_and_cache_grid_html for backoff scaling
        grid_html = fetch_and_cache_grid_html(
            session,
            booking_date,
            cache_dir=cache_dir,
            min_delay=1,
            max_delay=10,
            base=1.5,
        )
        if not grid_html:
            print(f"[ERROR] Failed to get grid HTML for {booking_date}.")
            day_offset += 1
            continue
        result = parse_grid_html(grid_html, date=booking_date)
        crew_list = result.get("crew_availability", [])
        daily_crew_lists.append(crew_list)
        # Aggregate and check statuses
        crew_list_agg = aggregate_crew_availability(daily_crew_lists)
        # Check if all crew have both next_available and next_available_until determined (not None)
        all_statuses_determined = all(
            (
                crew["next_available"] is not None
                and crew["next_available_until"] is not None
            )
            for crew in crew_list_agg
        )
        day_offset += 1
    # Output as a list of crew
    with open("gridAvail.json", "w", encoding="utf-8") as f:
        json.dump(crew_list_agg, f, indent=2)
    print(
        f"[OK] Saved crew availability for {len(crew_list_agg)} crew members to gridAvail.json"
    )
    undetermined = [
        crew["name"]
        for crew in crew_list_agg
        if (
            (crew["next_available"] is None or crew["next_available_until"] is None)
            and crew.get("available_for") != ">72h"
        )
    ]
    got_72h = [
        crew["name"] for crew in crew_list_agg if crew.get("available_for") == ">72h"
    ]
    if all_statuses_determined:
        print(f"[OK] Got all upcoming availability (for {day_offset} days)")
    elif undetermined:
        print(
            f"[WARN] Could not get all upcoming availability after searching {max_days} days for crew members: {', '.join(undetermined)}"
        )
    elif got_72h:
        print(
            f"[OK] Got at least 72 hours availability for crew after searching {day_offset} days: {', '.join(got_72h)}"
        )
