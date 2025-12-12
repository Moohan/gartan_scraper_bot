"""Fetches the HTML content of the real-time station display page."""

from gartan_fetch import AuthenticationError, gartan_login_and_get_session
from utils import log_debug

STATION_DISPLAY_URL = (
    "https://scottishfrs-availability.gartantech.com/StationDisplay.aspx?id=P22"
)


def fetch_station_display_html():
    """
    Fetches the HTML of the real-time station display page.

    Returns:
        str: The HTML content of the page, or None if an error occurs.
    """
    try:
        session = gartan_login_and_get_session()
        response = session.get(STATION_DISPLAY_URL)
        response.raise_for_status()
        return response.text
    except AuthenticationError as e:
        log_debug("error", f"Authentication failed while fetching station display: {e}")
        return None
    except Exception as e:
        log_debug("error", f"An error occurred while fetching station display: {e}")
        return None


if __name__ == "__main__":
    html = fetch_station_display_html()
    if html:
        print("Successfully fetched station display HTML.")
        with open("station_display.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("HTML content saved to station_display.html")
    else:
        print("Failed to fetch station display HTML.")
