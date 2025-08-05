import os
import pytest
from test_compatibility import fetch_grid_html_and_date, login_gartan
from gartan_fetch import (
    gartan_login_and_get_session,
    fetch_grid_html_for_date,
    fetch_and_cache_grid_html,
)


def test_fetch_grid_html(monkeypatch):
    """Test fetching grid HTML with legacy compatibility."""
    monkeypatch.setenv("GARTAN_USERNAME", "test_user")
    monkeypatch.setenv("GARTAN_PASSWORD", "test_pass")

    session = gartan_login_and_get_session()
    html, date = fetch_grid_html_and_date(session, "2025-07-01")
    assert html is not None
    assert "<table" in html.lower()  # Grid table instead of full HTML
    assert date == "01/07/2025"  # Date format converted

    # Test caching
    booking_date = "02/08/2025"
    grid_html = fetch_and_cache_grid_html(session, booking_date)
    assert grid_html is not None
    assert "<table" in grid_html

    # Should use cache on second call
    grid_html2 = fetch_and_cache_grid_html(session, booking_date)

    def normalize(html):
        import re

        # Remove all whitespace between tags and strip
        html = re.sub(r">\s+<", "><", html)
        # Remove script/style blocks (dynamic content)
        html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        return html.strip()

    assert normalize(grid_html2) == normalize(grid_html)


def test_fetch_grid_html_for_date():
    session = gartan_login_and_get_session()
    booking_date = "02/08/2025"
    grid_html = fetch_grid_html_for_date(session, booking_date)
    assert grid_html is not None
    assert "<table" in grid_html
