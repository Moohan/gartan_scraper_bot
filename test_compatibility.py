"""Legacy compatibility module for tests."""

from gartan_fetch import gartan_login_and_get_session, fetch_grid_html_for_date

# For backward compatibility with tests
login_gartan = gartan_login_and_get_session


def fetch_grid_html_and_date(session, date_str):
    """Legacy wrapper for test compatibility."""
    if "-" in date_str:
        # Convert YYYY-MM-DD to DD/MM/YYYY
        year, month, day = date_str.split("-")
        date_str = f"{day}/{month}/{year}"

    html = fetch_grid_html_for_date(session, date_str)
    return html, date_str
