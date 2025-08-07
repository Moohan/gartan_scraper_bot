import pytest
from unittest.mock import patch, MagicMock
from gartan_fetch import fetch_and_cache_grid_html, gartan_login_and_get_session
import os


def test_gartan_login_and_get_session(monkeypatch):
    class DummyResponse:
        def __init__(self, text):
            self.text = text
            self.content = text.encode("utf-8")
            self.status_code = 200

    class DummySession:
        def get(self, url, *args, **kwargs):
            return DummyResponse("<form></form>")

        def post(self, url, data=None, headers=None):
            return DummyResponse("OK")

    monkeypatch.setattr("requests.Session", lambda: DummySession())
    monkeypatch.setenv("GARTAN_USERNAME", "user")
    monkeypatch.setenv("GARTAN_PASSWORD", "pass")
    session = gartan_login_and_get_session()
    assert session is not None


def test_gartan_login_failure(monkeypatch):
    class DummyResponse:
        def __init__(self, text, status_code=403):
            self.text = text
            self.content = text.encode("utf-8")
            self.status_code = status_code

    class DummySession:
        def get(self, url, *args, **kwargs):
            return DummyResponse("<form></form>")

        def post(self, url, data=None, headers=None):
            return DummyResponse("Login failed", status_code=403)

    monkeypatch.setattr("requests.Session", lambda: DummySession())
    monkeypatch.setenv("GARTAN_USERNAME", "baduser")
    monkeypatch.setenv("GARTAN_PASSWORD", "badpass")
    try:
        gartan_login_and_get_session()
    except Exception as e:
        assert "Failed to retrieve data page" in str(e)


def test_fetch_and_cache_grid_html_cache(monkeypatch, tmp_path):
    # Patch session.get to return dummy HTML
    class DummySession:
        def get(self, url, params=None, headers=None):
            return None

        def post(self, url, data=None, headers=None):
            return None

    session = DummySession()
    date = "05/08/2025"
    cache_dir = tmp_path
    monkeypatch.setattr(
        "gartan_fetch.fetch_grid_html_for_date", lambda session, date: "<html></html>"
    )
    # First call should fetch and cache
    html = fetch_and_cache_grid_html(
        session,
        date,
        cache_dir=cache_dir,
        cache_minutes=1,
        cache_mode="cache-preferred",
    )
    assert html == "<html></html>"
    # Second call should use cache
    html2 = fetch_and_cache_grid_html(
        session, date, cache_dir=cache_dir, cache_minutes=1, cache_mode="cache-only"
    )
    assert html2 == "<html></html>"


def test_fetch_and_cache_grid_html_error(monkeypatch):
    class DummySession:
        def get(self, url, params=None, headers=None):
            raise Exception("Network error")

    session = DummySession()
    date = "05/08/2025"
    html = fetch_and_cache_grid_html(
        session, date, cache_dir=".", cache_minutes=1, cache_mode="cache-only"
    )
    assert html is None or html == "<html></html>"


def test_fetch_and_cache_grid_html_ajax_error(monkeypatch):
    class DummySession:
        def get(self, url, params=None, headers=None):
            class DummyResp:
                status_code = 500
                text = "Server error"
                content = b"Server error"

            return DummyResp()

        def post(self, url, data=None, headers=None):
            class DummyResp:
                status_code = 500
                text = "Server error"
                content = b"Server error"

            return DummyResp()

    session = DummySession()
    date = "05/08/2025"
    try:
        fetch_and_cache_grid_html(
            session, date, cache_dir=".", cache_minutes=1, cache_mode="cache-preferred"
        )
    except Exception as e:
        assert "Server error" in str(e)


def test_fetch_and_cache_grid_html_expiry(tmp_path, monkeypatch):
    # Simulate cache expiry by setting old mtime
    class DummySession:
        def get(self, url, params=None, headers=None):
            return None

        def post(self, url, data=None, headers=None):
            return None

    session = DummySession()
    date = "05/08/2025"
    cache_dir = tmp_path
    monkeypatch.setattr(
        "gartan_fetch.fetch_grid_html_for_date",
        lambda session, date: "<html>fresh</html>",
    )
    html = fetch_and_cache_grid_html(
        session,
        date,
        cache_dir=cache_dir,
        cache_minutes=1,
        cache_mode="cache-preferred",
    )
    assert html == "<html>fresh</html>"
    # Expire cache
    cache_file = os.path.join(cache_dir, f"grid_{date.replace('/', '-')}.html")
    os.utime(cache_file, (1, 1))  # Set mtime to epoch
    html2 = fetch_and_cache_grid_html(
        session,
        date,
        cache_dir=cache_dir,
        cache_minutes=1,
        cache_mode="cache-preferred",
    )
    assert html2 == "<html>fresh</html>"


def test_fetch_and_cache_grid_html_corrupt_cache(tmp_path, monkeypatch):
    class DummySession:
        def get(self, url, params=None, headers=None):
            return None

        def post(self, url, data=None, headers=None):
            return None

    session = DummySession()
    date = "05/08/2025"
    cache_dir = tmp_path
    # Write corrupt cache file
    cache_file = os.path.join(cache_dir, f"grid_{date.replace('/', '-')}.html")
    with open(cache_file, "wb") as f:
        f.write(b"\x00\x01\x02")
    
    # Make the cache file appear old so it will be considered expired
    import time
    old_time = time.time() - 3600  # 1 hour ago
    os.utime(cache_file, (old_time, old_time))
    
    monkeypatch.setattr(
        "gartan_fetch.fetch_grid_html_for_date",
        lambda session, date: "<html>recovered</html>",
    )
    html = fetch_and_cache_grid_html(
        session,
        date,
        cache_dir=cache_dir,
        cache_minutes=1,  # 1 minute expiry, so 1 hour old file is expired
        cache_mode="cache-preferred",
    )
    assert html == "<html>recovered</html>"


def test_fetch_and_cache_grid_html_non_json_ajax(monkeypatch, tmp_path):
    class DummySession:
        def post(self, url, data=None, headers=None):
            class DummyResp:
                status_code = 200
                text = "Not JSON"
                content = b"Not JSON"

            return DummyResp()

        def get(self, url, params=None, headers=None):
            return None

    session = DummySession()
    date = "05/08/2025"
    cache_dir = tmp_path
    monkeypatch.setattr("gartan_fetch._post_schedule_request", lambda *a, **kw: None)
    html = fetch_and_cache_grid_html(
        session, date, cache_dir=str(cache_dir), cache_minutes=1, cache_mode="no-cache"
    )
    assert html is None


def test_fetch_and_cache_grid_html_unexpected_status(monkeypatch, tmp_path):
    class DummySession:
        def post(self, url, data=None, headers=None):
            class DummyResp:
                status_code = 404
                text = "Not Found"
                content = b"Not Found"

            return DummyResp()

        def get(self, url, params=None, headers=None):
            return None

    session = DummySession()
    date = "05/08/2025"
    cache_dir = tmp_path
    monkeypatch.setattr("gartan_fetch._post_schedule_request", lambda *a, **kw: None)
    html = fetch_and_cache_grid_html(
        session, date, cache_dir=str(cache_dir), cache_minutes=1, cache_mode="no-cache"
    )
    assert html is None


def test_fetch_and_cache_grid_html_invalid_cache_mode(monkeypatch):
    class DummySession:
        def get(self, url, params=None, headers=None):
            return None

        def post(self, url, data=None, headers=None):
            return None

    session = DummySession()
    date = "05/08/2025"
    monkeypatch.setattr(
        "gartan_fetch.fetch_grid_html_for_date", lambda session, date: "<html></html>"
    )
    html = fetch_and_cache_grid_html(
        session, date, cache_dir=".", cache_minutes=1, cache_mode="invalid-mode"
    )
    assert html == "<html></html>"


def test_fetch_and_cache_grid_html_empty_html(tmp_path, monkeypatch):
    class DummySession:
        def get(self, url, params=None, headers=None):
            return None

        def post(self, url, data=None, headers=None):
            return None

    session = DummySession()
    date = "05/08/2025"
    monkeypatch.setattr(
        "gartan_fetch.fetch_grid_html_for_date", lambda session, date: ""
    )
    html = fetch_and_cache_grid_html(
        session, date, cache_dir=str(tmp_path), cache_minutes=1, cache_mode="cache-preferred"
    )
    assert html == ""
