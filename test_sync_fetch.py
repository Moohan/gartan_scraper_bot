import os
import requests
from gartan_fetch import gartan_login_and_get_session, fetch_grid_html_for_date, DATA_URL
from dotenv import load_dotenv

load_dotenv()

def test_sync_fetch():
    print("Attempting login...")
    session = gartan_login_and_get_session()
    if not session:
        print("Login failed (returned None)")
        return

    date = "06/01/2026"
    print(f"Attempting sync fetch for {date}...")

    # Debug: Check the main page content
    print(f"Fetching main page: {DATA_URL}")
    main_page_resp = session.get(DATA_URL)
    print(f"Main page status: {main_page_resp.status_code}")
    print(f"Main page URL: {main_page_resp.url}")

    # Save a snippet of the main page to a file for manual inspection if needed
    with open("main_page_debug.html", "w", encoding="utf-8") as f:
        f.write(main_page_resp.text)
    print("Saved main page to main_page_debug.html")

    html = fetch_grid_html_for_date(session, date)

    if html:
        print(f"Success! HTML length: {len(html)}")
        print("First 200 chars:")
        print(html[:200])
    else:
        print("Fetch failed (returned None or empty)")

if __name__ == "__main__":
    test_sync_fetch()
