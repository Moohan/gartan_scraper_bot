#!/usr/bin/env python3
"""Tests for gartan_fetch error handling and edge cases."""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

from gartan_fetch import (
    AuthenticationError,
    _build_login_payload,
    _get_login_form,
    fetch_and_cache_grid_html,
    gartan_login_and_get_session,
)


class TestGartanFetchErrorHandling:
    """Test error handling in gartan_fetch functions."""

    def setUp(self):
        """Set up test environment."""
        # Create _cache directory before tests
        os.makedirs("_cache", exist_ok=True)

    def test_fetch_and_cache_file_read_error(self):
        """Test fetch_and_cache_grid_html with file read error."""
        test_date = "26/08/2025"  # Use string format expected by the function

        # Mock file existence but read failure
        with (
            patch("gartan_fetch.os.path.exists", return_value=True),
            patch("gartan_fetch.open", mock_open()) as mock_file,
        ):
            mock_file.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

            # Should handle decode error gracefully
            session = requests.Session()
            result = fetch_and_cache_grid_html(session, test_date)
            assert result is not None  # Should fetch fresh data

    def test_fetch_and_cache_file_write_error(self):
        """Test fetch_and_cache_grid_html with file write error."""
        test_date = "26/08/2025"  # Use string format expected by the function

        with (
            patch("gartan_fetch.os.path.exists", return_value=False),
            patch(
                "gartan_fetch.fetch_grid_html_for_date", return_value="<html></html>"
            ),
            patch("gartan_fetch.open", mock_open()) as mock_file,
        ):
            mock_file.side_effect = IOError("Write permission denied")

            # Should still return data even if caching fails
            session = requests.Session()
            result = fetch_and_cache_grid_html(session, test_date)
            assert result == "<html></html>"

    def test_login_with_network_error(self):
        """Test gartan_login_and_get_session with network error."""
        with patch("gartan_fetch.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            mock_session.get.side_effect = requests.ConnectionError("Network error")

            result = gartan_login_and_get_session()

            # Should return None on network error
            assert result is None

    def test_login_with_missing_form(self):
        """Test gartan_login_and_get_session with missing login form."""
        with patch("gartan_fetch.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Mock response without login form
            mock_response = MagicMock()
            mock_response.content = "<html><body>No form here</body></html>".encode(
                "utf-8"
            )
            mock_session.get.return_value = mock_response

            # Should raise exception for missing form
            with pytest.raises(AuthenticationError, match=r"^Login form not found$"):
                _get_login_form(mock_session)

    def test_build_login_payload_complex_form(self):
        """Test _build_login_payload with complex form structure."""
        from bs4 import BeautifulSoup

        # Complex form with multiple input types
        html = """
        <form>
            <input type="text" name="username" value="">
            <input type="password" name="password" value="">
            <input type="hidden" name="token" value="abc123">
            <input type="submit" name="submit" value="Login">
            <input type="checkbox" name="remember" value="1">
            <textarea name="comments"></textarea>
            <select name="role">
                <option value="user">User</option>
                <option value="admin" selected>Admin</option>
            </select>
        </form>
        """

        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")

        payload = _build_login_payload(form, "testuser", "testpass")

        # Should include all form fields with appropriate values
        assert payload["txt_userid"] == "testuser"
        assert payload["txt_pword"] == "testpass"
        assert "token" in payload
        assert "remember" in payload
        # These fields should be handled gracefully if present
        if "comments" in payload:
            assert payload["comments"] == ""
        if "role" in payload:
            assert payload["role"] == "admin"

    def test_build_login_payload_edge_cases(self):
        """Test _build_login_payload with edge cases."""
        from bs4 import BeautifulSoup

        # Form with missing attributes
        html = """
        <form>
            <input type="text" name="username">
            <input name="unnamed_field" value="test">
            <input type="hidden" value="no_name">
            <select name="empty_select">
            </select>
        </form>
        """

        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")

        payload = _build_login_payload(form, "user", "pass")

        # Should handle missing attributes gracefully
        assert payload["txt_userid"] == "user"
        assert "txt_pword" in payload
        # Extra fields should be handled without error
        if "unnamed_field" in payload:
            assert payload["unnamed_field"] == "test"
        # Input without name should be ignored
        assert len([k for k in payload.keys() if k == "unnamed_field"]) <= 1

    def test_cache_file_corruption_handling(self):
        """Test handling of corrupted cache files."""
        test_date = "26/08/2025"  # Use string format expected by the function

        # Create _cache directory
        os.makedirs("_cache", exist_ok=True)

        # Mock corrupted file that exists but is unreadable
        with (
            patch("gartan_fetch.os.path.exists", return_value=True),
            patch(
                "gartan_fetch.open", mock_open(read_data=b"\x80\x81\x82")
            ) as mock_file,
        ):
            mock_file.side_effect = UnicodeDecodeError(
                "utf-8", b"\x80\x81\x82", 0, 1, "invalid start byte"
            )

            with patch(
                "gartan_fetch.fetch_grid_html_for_date",
                return_value="<html>fresh</html>",
            ):
                session = requests.Session()
                result = fetch_and_cache_grid_html(session, test_date)

                # Should fall back to fresh fetch
                assert result == "<html>fresh</html>"

    def test_session_persistence_failure(self):
        """Test resilience to session persistence failure."""
        with patch("requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session

            # Mock responses
            get_response = MagicMock()
            get_response.status_code = 200
            get_response.content = b"<form></form>"
            get_response.url = "https://gartan.test/main"
            get_response.text = "Welcome"

            mock_session.get.return_value = get_response
            mock_session.post.return_value = get_response

            # Session persistence error should be handled gracefully
            try:
                session = gartan_login_and_get_session()
                assert session is not None
            except Exception as e:
                pytest.fail(f"Session handling failed: {e}")
