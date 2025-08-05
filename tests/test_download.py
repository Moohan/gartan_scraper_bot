import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from gartan_fetch import gartan_login_and_get_session, fetch_and_cache_grid_html


def test_download_grid_html():
    """Test that grid HTML is downloaded and contains expected table."""
    session = gartan_login_and_get_session()
    booking_date = "02/08/2025"
    grid_html = fetch_and_cache_grid_html(session, booking_date)
    assert grid_html is not None
    assert "<table" in grid_html
    assert "gridAvail" in grid_html
