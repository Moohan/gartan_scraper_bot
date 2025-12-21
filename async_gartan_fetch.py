"""
Asynchronous fetching for Gartan schedule HTML using aiohttp.
"""

import aiohttp
import json

from utils import log_debug

# Constants from gartan_fetch.py
BASE_URL = "https://scottishfrs-availability.gartantech.com/"
DATA_URL = f"{BASE_URL}Availability/Schedule/AvailabilityMain1.aspx?UseDefaultStation=1"
SCHEDULE_URL = f"{BASE_URL}Availability/Schedule/AvailabilityMain1.aspx/GetSchedule"

def _build_schedule_payload(booking_date: str) -> dict:
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

def _get_schedule_headers() -> dict:
    """
    Return headers for the schedule AJAX request.
    """
    return {
        "Referer": DATA_URL,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
    }

async def fetch_grid_html_for_date_async(session: aiohttp.ClientSession, booking_date: str) -> str | None:
    """
    Given an authenticated aiohttp session and a booking_date (str, dd/mm/yyyy),
    fetch the grid HTML for that date asynchronously.
    Returns grid_html or None.
    """
    payload = _build_schedule_payload(booking_date)
    headers = _get_schedule_headers()

    # Bolt ⚡: Asynchronously fetches daily schedule HTML, allowing for concurrent network requests.
    # This is much more efficient than the previous threaded approach for I/O-bound tasks.
    try:
        async with session.post(SCHEDULE_URL, headers=headers, json=payload) as response:
            if response.status != 200:
                log_debug(
                    "error",
                    f"Async schedule AJAX failed for {booking_date}: {response.status}",
                )
                return None

            # The response is JSON, with the HTML content in the 'd' key.
            data = await response.json()
            grid_html = data.get("d", "")
            return grid_html
    except aiohttp.ClientError as e:
        log_debug("error", f"Could not fetch or extract grid HTML for {booking_date}: {e}")
        return None
    except json.JSONDecodeError as e:
        log_debug("error", f"Could not decode JSON response for {booking_date}: {e}")
        return None
