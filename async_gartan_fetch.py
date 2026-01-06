"""
Asynchronous fetching for Gartan schedule HTML using aiohttp.
"""

import json

import aiohttp

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
        "brigadeId": "101",
        "brigadeName": "P22",
        "employeeBrigadeId": 0,
        "bookingDate": booking_date,
        "resolution": 60,
        "dayCount": 0,
        "showDetails": True,
        "showHours": True,
        "highlightContractDetails": False,
        "highlightEmployeesOffStation": True,
        "includeApplianceStatus": True,
        "showEmpShiftTypes": False,
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


async def fetch_grid_html_for_date_async(
    session: aiohttp.ClientSession, booking_date: str
) -> str | None:
    """
    Given an authenticated aiohttp session and a booking_date (str, dd/mm/yyyy),
    fetch the grid HTML for that date asynchronously.
    Returns grid_html or None.
    """
    payload = _build_schedule_payload(booking_date)
    headers = _get_schedule_headers()

    # Manually construct the payload string to match Gartan's frontend JS exactly (unquoted keys, single-quoted values)
    # See js_fsi3.js line 275
    raw_payload = (
        "{"
        f" brigadeId: {payload['brigadeId']},"
        f" brigadeName: '{payload['brigadeName']}',"
        f" employeeBrigadeId: {payload['employeeBrigadeId']},"
        f" bookingDate: '{payload['bookingDate']}',"
        f" resolution: {payload['resolution']},"
        f" dayCount: {payload['dayCount']},"
        f" showDetails: '{str(payload['showDetails']).lower()}',"
        f" showHours: '{str(payload['showHours']).lower()}',"
        f" highlightContractDetails: '{str(payload['highlightContractDetails']).lower()}',"
        f" highlightEmployeesOffStation: '{str(payload['highlightEmployeesOffStation']).lower()}',"
        f" includeApplianceStatus: '{str(payload['includeApplianceStatus']).lower()}',"
        f" showEmpShiftTypes: '{str(payload['showEmpShiftTypes']).lower()}'"
        "}"
    )

    try:
        async with session.post(
            SCHEDULE_URL, headers=headers, data=raw_payload
        ) as response:
            if response.status != 200:
                log_debug(
                    "error",
                    f"Async schedule AJAX failed for {booking_date}: {response.status}",
                )
                # Log response body for debugging
                body = await response.text()
                log_debug("error", f"Response body: {body}")
                return None

            # The response is JSON, with the HTML content in the 'd' key.
            data = await response.json()
            grid_html = data.get("d", "")
            return grid_html
    except aiohttp.ClientError as e:
        log_debug(
            "error", f"Could not fetch or extract grid HTML for {booking_date}: {e}"
        )
        return None
    except json.JSONDecodeError as e:
        log_debug("error", f"Could not decode JSON response for {booking_date}: {e}")
        return None
