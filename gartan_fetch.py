from datetime import datetime as dt, timedelta
from utils import log_debug


def fetch_and_cache_grid_html(
    session,
    booking_date,
    cache_dir="_cache",
    cache_minutes=15,
    min_delay=1,
    max_delay=10,
    base=1.5,
    cache_mode=None,
):
    """
    Fetch grid HTML for a given date, using cache if available and fresh.
    Handles exponential backoff between fetches.
    Returns grid_html (str or None).
    cache_mode: None (default), 'no-cache', 'cache-first', 'cache-only'
    """
    import os, time, random

    cache_file = os.path.join(cache_dir, f"grid_{booking_date.replace('/', '-')}.html")
    use_cache = False
    cache_exists = os.path.exists(cache_file)
    grid_html = None

    # Handle cache modes
    if cache_mode == "no-cache":
        # Always fetch, ignore cache
        print(
            f"[NO-CACHE] Downloading fresh grid HTML for {booking_date} (ignoring cache)..."
        )
        log_debug("fetch", f"[no-cache] Fetching grid HTML for {booking_date}...")
        grid_html = _fetch_and_write_cache(session, booking_date, cache_file)
        _perform_delay(min_delay, max_delay, base)
        return grid_html

    elif cache_mode == "cache-first":
        # Use cache if exists, even if stale
        if cache_exists:
            print(
                f"[CACHE-FIRST] Using cached grid HTML for {booking_date} (cache exists, not downloading)..."
            )
            log_debug(
                "cache", f"[cache-first] Using cached grid HTML for {booking_date}."
            )
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    grid_html = f.read()
                # No delay for cache
                return grid_html
            except (UnicodeDecodeError, IOError) as e:
                print(f"[CACHE-FIRST] Cache file corrupted, downloading fresh data: {e}")
                log_debug("cache", f"[cache-first] Cache corrupted, fetching fresh: {e}")
                grid_html = _fetch_and_write_cache(session, booking_date, cache_file)
                _perform_delay(min_delay, max_delay, base)
                return grid_html
        else:
            print(
                f"[CACHE-FIRST] Downloading grid HTML for {booking_date} (no cache found)..."
            )
            log_debug(
                "fetch", f"[cache-first] Fetching grid HTML for {booking_date}..."
            )
            grid_html = _fetch_and_write_cache(session, booking_date, cache_file)
            _perform_delay(min_delay, max_delay, base)
            return grid_html

    elif cache_mode == "cache-only":
        # Only use cache, never fetch
        if cache_exists:
            print(
                f"[CACHE-ONLY] Using cached grid HTML for {booking_date} (cache exists, not downloading)..."
            )
            log_debug(
                "cache", f"[cache-only] Using cached grid HTML for {booking_date}."
            )
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    grid_html = f.read()
                # No delay for cache
                return grid_html
            except (UnicodeDecodeError, IOError) as e:
                print(f"[CACHE-ONLY] Cache file corrupted: {e}")
                log_debug("cache", f"[cache-only] Cache corrupted: {e}")
                return None
        else:
            print(
                f"[CACHE-ONLY] No cached grid HTML for {booking_date} (no cache found, not downloading)..."
            )
            log_debug("cache", f"[cache-only] No cached grid HTML for {booking_date}.")
            return None

    # Default: check cache expiry
    if _is_cache_valid(cache_file, cache_minutes):
        print(f"[CACHE] Using cached grid HTML for {booking_date} (cache is fresh)...")
        log_debug("cache", f"Using cached grid HTML for {booking_date}.")
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                grid_html = f.read()
            # No delay for cache
            return grid_html
        except (UnicodeDecodeError, IOError) as e:
            print(f"[CACHE] Cache file corrupted, downloading fresh data: {e}")
            log_debug("cache", f"Cache corrupted, fetching fresh: {e}")
            # Fall through to fetch fresh data

    print(
        f"[FETCH] Downloading grid HTML for {booking_date} (cache expired or missing)..."
    )
    log_debug("fetch", f"Fetching grid HTML for {booking_date}...")
    grid_html = _fetch_and_write_cache(session, booking_date, cache_file)
    _perform_delay(min_delay, max_delay, base)
    return grid_html


def _is_cache_valid(cache_file: str, cache_minutes: int) -> bool:
    """Check if the cache file exists and is not expired."""
    if not os.path.exists(cache_file):
        return False
    mtime = os.path.getmtime(cache_file)
    if (dt.now() - dt.fromtimestamp(mtime)).total_seconds() / 60 < cache_minutes:
        return True
    return False


def _fetch_and_write_cache(session, booking_date, cache_file):
    """Fetch grid HTML and write it to the cache file."""
    grid_html = fetch_grid_html_for_date(session, booking_date)
    if grid_html:
        with open(cache_file, "w", encoding="utf-8") as f:
            f.write(grid_html)
    return grid_html


def _perform_delay(min_delay, max_delay, base):
    """Perform a randomized delay between fetches."""
    import time, random

    delay = min(max_delay, min_delay * (base ** max(0, 0)))
    actual_delay = random.uniform(min_delay, delay)
    if actual_delay >= 2:
        log_debug("wait", f"Waiting {actual_delay:.1f}s before next fetch.")
        for i in range(int(actual_delay), 0, -1):
            log_debug("wait", f"{i} seconds left before next fetch.")
            time.sleep(1)
        leftover = actual_delay - int(actual_delay)
        if leftover > 0:
            time.sleep(leftover)
    else:
        time.sleep(actual_delay)


import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from datetime import datetime
from connection_manager import get_session_manager
from typing import Optional


# Load environment variables
load_dotenv()

LOGIN_URL = (
    "https://grampianrds.firescotland.gov.uk/GartanAvailability/Account/Login.aspx"
)
DATA_URL = "https://grampianrds.firescotland.gov.uk/GartanAvailability/Availability/Schedule/AvailabilityMain1.aspx?UseDefaultStation=1"
USERNAME = os.environ.get("GARTAN_USERNAME")
PASSWORD = os.environ.get("GARTAN_PASSWORD")

# Session cache for authenticated sessions
_authenticated_session = None
_session_authenticated_time = None
_session_timeout = 1800  # 30 minutes


def gartan_login_and_get_session():
    """
    Get an authenticated session, reusing existing session if still valid.
    Returns an authenticated requests.Session().
    Raises AssertionError if credentials are missing.
    """
    global _authenticated_session, _session_authenticated_time
    import time
    
    assert (
        USERNAME and PASSWORD
    ), "GARTAN_USERNAME and GARTAN_PASSWORD must be set in .env"
    
    current_time = time.time()
    
    # Check if we have a valid cached session
    if (_authenticated_session is not None and 
        _session_authenticated_time is not None and
        (current_time - _session_authenticated_time) < _session_timeout):
        log_debug("session", "Reusing existing authenticated session")
        return _authenticated_session
    
    # Create new authenticated session
    try:
        session_manager = get_session_manager()
        session = session_manager.get_session()
    except Exception:
        # Fallback to basic session for testing compatibility
        import requests
        session = requests.Session()
    
    log_debug("session", "Creating new authenticated session")
    
    form, resp = _get_login_form(session)
    post_url = _get_login_post_url(form)
    payload = _build_login_payload(form, USERNAME, PASSWORD)
    headers = _get_login_headers()
    _post_login(session, post_url, payload, headers)
    _get_data_page(session, headers)
    
    # Cache the authenticated session
    _authenticated_session = session
    _session_authenticated_time = current_time
    
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
        log_debug("error", f"Login POST failed with status: {login_resp.status_code}")


def _get_data_page(session, headers):
    """
    Retrieve the main data page after login to confirm authentication.
    """
    data_resp = session.get(DATA_URL, headers=headers)
    if data_resp.status_code != 200:
        log_debug("error", f"Failed to retrieve data page: {data_resp.status_code}")
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


# CLI for direct testing of cache modes
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test grid HTML fetch/caching with cache modes."
    )
    parser.add_argument("date", help="Booking date (dd/mm/yyyy)")
    parser.add_argument(
        "--no-cache", action="store_true", help="Always download, ignore cache"
    )
    parser.add_argument(
        "--cache-first", action="store_true", help="Use cache if exists, even if stale"
    )
    parser.add_argument(
        "--cache-only", action="store_true", help="Only use cache, never download"
    )
    parser.add_argument(
        "--cache-minutes",
        type=int,
        default=15,
        help="Cache expiry window in minutes (default 15)",
    )
    args = parser.parse_args()

    # Determine cache_mode
    cache_mode = None
    if args.no_cache:
        cache_mode = "no-cache"
    elif args.cache_first:
        cache_mode = "cache-first"
    elif args.cache_only:
        cache_mode = "cache-only"

    print(f"[INFO] Running with cache_mode={cache_mode}, date={args.date}")
    session = gartan_login_and_get_session()
    html = fetch_and_cache_grid_html(
        session,
        args.date,
        cache_minutes=args.cache_minutes,
        cache_mode=cache_mode,
    )
    if html:
        print(f"[SUCCESS] Grid HTML fetched for {args.date} (length={len(html)})")
    else:
        print(f"[FAIL] No grid HTML for {args.date}")


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
        log_debug(
            "error",
            f"Schedule AJAX failed for {booking_date}: {schedule_resp.status_code}",
        )
    try:
        grid_html = schedule_resp.json().get("d", "")
        return grid_html
    except Exception as e:
        log_debug("error", f"Could not extract grid HTML for {booking_date}: {e}")
        return None
