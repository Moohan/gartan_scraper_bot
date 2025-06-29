from gartan_fetch import (
    gartan_login_and_get_session,
    fetch_grid_html_for_date,
)
from parse_grid import parse_grid_html
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
    crew_dict = {}
    all_slots = []
    cache_dir = "_cache"
    os.makedirs(cache_dir, exist_ok=True)
    day_offset = 0
    all_statuses_determined = False
    max_days = 14
    while not all_statuses_determined and day_offset < max_days:
        booking_date = (today + timedelta(days=day_offset)).strftime("%d/%m/%Y")
        cache_file = os.path.join(
            cache_dir, f"grid_{booking_date.replace('/', '-')}.html"
        )
        use_cache = False
        if os.path.exists(cache_file):
            mtime = os.path.getmtime(cache_file)
            age = time.time() - mtime
            if age < 15 * 60:  # 15 minutes
                use_cache = True
        if use_cache:
            print(f"[CACHE] Using cached grid HTML for {booking_date}.")
            with open(cache_file, "r", encoding="utf-8") as f:
                grid_html = f.read()
        else:
            print(f"[FETCH] Fetching grid HTML for {booking_date}...")
            grid_html = fetch_grid_html_for_date(session, booking_date)
            if grid_html:
                with open(cache_file, "w", encoding="utf-8") as f:
                    f.write(grid_html)
            # Exponential backoff: delay increases as more days are fetched
            base = 1.5
            min_delay = 1
            max_delay = 10
            delay = min(max_delay, min_delay * (base ** max(0, day_offset - 1)))
            actual_delay = random.uniform(min_delay, delay)
            if actual_delay >= 2:
                print(
                    f"[WAIT] Waiting {actual_delay:.1f}s before next fetch: ",
                    end="",
                    flush=True,
                )
                import sys

                for i in range(int(actual_delay), 0, -1):
                    print(f"{i} ", end="", flush=True)
                    time.sleep(1)
                leftover = actual_delay - int(actual_delay)
                if leftover > 0:
                    time.sleep(leftover)
                print()
            else:
                time.sleep(actual_delay)
        if not grid_html:
            print(f"[ERROR] Failed to get grid HTML for {booking_date}.")
            day_offset += 1
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
        # After each day, check if all statuses are determined
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
            next_avail_until = None
            available_now = False
            available_for = None
            for idx, (slot_dt, avail) in enumerate(slot_tuples):
                if slot_dt >= now:
                    if avail:
                        if idx == 0 and slot_dt <= now:
                            available_now = True
                        elif slot_dt <= now:
                            available_now = True
                        next_avail = slot_dt.strftime("%d/%m/%Y %H:%M")
                        available_hours = None
                        for j in range(idx + 1, len(slot_tuples)):
                            next_dt, next_avail_val = slot_tuples[j]
                            hours_since_avail = (
                                next_dt - slot_dt
                            ).total_seconds() / 3600.0
                            if not next_avail_val:
                                next_avail_until = next_dt.strftime("%d/%m/%Y %H:%M")
                                available_hours = hours_since_avail
                                break
                            if hours_since_avail >= 72:
                                available_hours = ">72"
                                break
                        if available_hours is None:
                            # If we reached the end and still available, check if last slot is >=72h
                            if len(slot_tuples) > idx + 1:
                                last_dt, last_avail = slot_tuples[-1]
                                hours_since_avail = (
                                    last_dt - slot_dt
                                ).total_seconds() / 3600.0
                                if last_avail and hours_since_avail >= 72:
                                    available_hours = ">72"
                        if available_hours == ">72":
                            available_for = ">72h"
                        elif isinstance(available_hours, (int, float)):
                            available_for = f"{round(available_hours, 2)}h"
                        else:
                            available_for = None
                        break
            crew["available_now"] = available_now
            crew["next_available"] = next_avail
            crew["next_available_until"] = next_avail_until
            crew["available_for"] = available_for
        # Check if all crew have both next_available and next_available_until determined (not None)
        all_statuses_determined = all(
            (
                crew["next_available"] is not None
                and crew["next_available_until"] is not None
            )
            for crew in crew_dict.values()
        )
        day_offset += 1
    # Clean up and output as a list of crew
    for crew in crew_dict.values():
        if "_all_slots" in crew:
            del crew["_all_slots"]
    crew_list = list(crew_dict.values())
    with open("gridAvail.json", "w", encoding="utf-8") as f:
        json.dump(crew_list, f, indent=2)
    print(
        f"[OK] Saved crew availability for {len(crew_list)} crew members to gridAvail.json"
    )
    undetermined = [
        crew["name"]
        for crew in crew_list
        if (
            (crew["next_available"] is None or crew["next_available_until"] is None)
            and crew.get("available_for") != ">72h"
        )
    ]
    got_72h = [
        crew["name"] for crew in crew_list if crew.get("available_for") == ">72h"
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
