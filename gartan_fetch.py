def fetch_and_cache_grid_html(
    session,
    booking_date,
    cache_dir="_cache",
    cache_minutes=15,
    min_delay=1,
    max_delay=10,
    base=1.5,
):
    """
    Fetch grid HTML for a given date, using cache if available and fresh.
    Handles exponential backoff between fetches.
    Returns grid_html (str or None).
    """
    import os, time, random

    cache_file = os.path.join(cache_dir, f"grid_{booking_date.replace('/', '-')}.html")
    use_cache = False
    if os.path.exists(cache_file):
        mtime = os.path.getmtime(cache_file)
        age = time.time() - mtime
        if age < cache_minutes * 60:
            use_cache = True
    if use_cache:
        print(f"[CACHE] Using cached grid HTML for {booking_date}.")
        with open(cache_file, "r", encoding="utf-8") as f:
            grid_html = f.read()
        return grid_html
    print(f"[FETCH] Fetching grid HTML for {booking_date}...")
    grid_html = fetch_grid_html_for_date(session, booking_date)
    if grid_html:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(grid_html)
    # Exponential backoff: delay increases as more days are fetched
    delay = min(
        max_delay, min_delay * (base ** max(0, 0))
    )  # day_offset handled by caller
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
    return grid_html


import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime


# Load environment variables
load_dotenv()

LOGIN_URL = (
    "https://grampianrds.firescotland.gov.uk/GartanAvailability/Account/Login.aspx"
)
DATA_URL = "https://grampianrds.firescotland.gov.uk/GartanAvailability/Availability/Schedule/AvailabilityMain1.aspx?UseDefaultStation=1"
USERNAME = os.environ.get("GARTAN_USERNAME")
PASSWORD = os.environ.get("GARTAN_PASSWORD")

assert USERNAME and PASSWORD, "GARTAN_USERNAME and GARTAN_PASSWORD must be set in .env"


def gartan_login_and_get_session():
    """
    Logs in to the Gartan system and returns an authenticated requests.Session().
    """
    session = requests.Session()
    form, resp = _get_login_form(session)
    post_url = _get_login_post_url(form)
    payload = _build_login_payload(form, USERNAME, PASSWORD)
    headers = _get_login_headers()
    _post_login(session, post_url, payload, headers)
    _get_data_page(session, headers)
    return session


def _get_login_form(session):
    """
    Retrieve the login form from the login page.
    Returns the form element and the response object.
    """
    resp = session.get(LOGIN_URL)
    soup = BeautifulSoup(resp.content, "html.parser")
    form = soup.find("form")
    if not form:
        raise Exception("[ERROR] Login form not found in login page HTML.")
    return form, resp


def _get_login_post_url(form):
    """
    Determine the POST URL for the login form.
    """
    action = form.get("action")
    if not action or not isinstance(action, str):
        return LOGIN_URL
    elif action.startswith("http"):
        return action
    else:
        from urllib.parse import urljoin

        return urljoin(LOGIN_URL, str(action))


def _build_login_payload(form, username, password):
    """
    Build the payload dictionary for the login POST request.
    """
    payload = {}
    try:
        input_tags = list(form.find_all("input"))
    except Exception:
        input_tags = [
            el for el in form.descendants if getattr(el, "name", None) == "input"
        ]
    for input_tag in input_tags:
        try:
            name = input_tag.get("name") if hasattr(input_tag, "get") else None
            if not name:
                continue
            value = input_tag.get("value", "") if hasattr(input_tag, "get") else ""
            payload[name] = value
        except Exception:
            continue
    # Overwrite with provided credentials
    payload["txt_userid"] = username
    payload["txt_pword"] = password
    # Ensure login button is present
    if "btnLogin" not in payload:
        login_button_value = "Sign In"
        for input_tag in input_tags:
            try:
                if hasattr(input_tag, "get") and input_tag.get("name") == "btnLogin":
                    login_button_value = input_tag.get("value", "Sign In")
                    break
            except Exception:
                continue
        payload["btnLogin"] = login_button_value
    return payload


def _get_login_headers():
    """
    Return headers for the login POST request.
    """
    return {
        "Referer": LOGIN_URL,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    }


def _post_login(session, post_url, payload, headers):
    """
    Perform the login POST request.
    """
    login_resp = session.post(post_url, data=payload, headers=headers)
    if login_resp.status_code != 200:
        print(f"[ERROR] Login POST failed with status: {login_resp.status_code}")


def _get_data_page(session, headers):
    """
    Retrieve the main data page after login to confirm authentication.
    """
    data_resp = session.get(DATA_URL, headers=headers)
    if data_resp.status_code != 200:
        raise Exception(
            f"[ERROR] Failed to retrieve data page: {data_resp.status_code}"
        )


def fetch_grid_html_for_date(session, booking_date):
    """
    Given an authenticated session and a booking_date (str, dd/mm/yyyy), fetch the grid HTML for that date.
    Returns grid_html or None.
    """
    import json

    schedule_url = "https://grampianrds.firescotland.gov.uk/GartanAvailability/Availability/Schedule/AvailabilityMain1.aspx/GetSchedule"
    payload = _build_schedule_payload(booking_date)
    headers = _get_schedule_headers()
    return _post_schedule_request(session, schedule_url, payload, headers, booking_date)


def _build_schedule_payload(booking_date):
    """
    Build the payload for the schedule AJAX request.
    """
    return {
        "brigadeId": 47,
        "brigadeName": "P22 Dunkeld",
        "employeeBrigadeId": 0,
        "bookingDate": booking_date,
        "resolution": 15,
        "dayCount": 0,
        "showDetails": "true",
        "showHours": "true",
        "highlightContractDetails": "false",
        "highlightEmployeesOffStation": "true",
        "includeApplianceStatus": "true",
    }


def _get_schedule_headers():
    """
    Return headers for the schedule AJAX request.
    """
    return {
        "Referer": DATA_URL,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }


def _post_schedule_request(session, schedule_url, payload, headers, booking_date):
    """
    Perform the AJAX request to fetch the schedule grid HTML for a given date.
    """
    import json

    schedule_resp = session.post(
        schedule_url, headers=headers, data=json.dumps(payload)
    )
    if schedule_resp.status_code != 200:
        print(
            f"[ERROR] Schedule AJAX failed for {booking_date}: {schedule_resp.status_code}"
        )
    try:
        grid_html = schedule_resp.json().get("d", "")
        return grid_html
    except Exception as e:
        print(f"[ERROR] Could not extract grid HTML for {booking_date}: {e}")
        return None
