from fetch_grid_html_and_date import (
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
    all_results = []
    for booking_date in date_strs:
        print(f"Fetching availability for {booking_date}...")
        grid_html = fetch_grid_html_for_date(session, booking_date)
        if not grid_html:
            print(f"Failed to fetch grid HTML for {booking_date}.")
            continue
        result = parse_grid_html(grid_html, date=booking_date)
        all_results.append(result)
        print(f"Parsed crew availability for date {booking_date}.")

    with open("gridAvail.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"Saved crew availability for {len(all_results)} days to gridAvail.json")
