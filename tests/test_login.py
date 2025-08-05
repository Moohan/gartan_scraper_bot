import os
import pytest
from test_compatibility import login_gartan


def test_login_success(monkeypatch):
    """Test successful login."""
    monkeypatch.setenv("GARTAN_USERNAME", "test_user")
    monkeypatch.setenv("GARTAN_PASSWORD", "test_pass")

    session = login_gartan()
    assert session is not None
    assert hasattr(session, "cookies")

    # Test the session works
    data_url = "https://grampianrds.firescotland.gov.uk/GartanAvailability/Availability/Schedule/AvailabilityMain1.aspx?UseDefaultStation=1"
    resp = session.get(data_url)
    assert resp.status_code == 200
    assert "Availability" in resp.text or "Crew" in resp.text


def test_login_missing_credentials():
    """Test login fails with missing credentials."""
    with pytest.raises(
        AssertionError, match="GARTAN_USERNAME and GARTAN_PASSWORD must be set in .env"
    ):
        login_gartan()
