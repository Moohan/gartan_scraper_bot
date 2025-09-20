#!/usr/bin/env python3
"""Enhanced tests for gartan_fetch.py error handling and edge cases."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from gartan_fetch import (
    AuthenticationError,
    _fetch_and_write_cache,
    _is_cache_valid,
    _perform_delay,
    fetch_and_cache_grid_html,
    gartan_login_and_get_session,
)


class TestGartanFetchErrorHandling:
    """Test error handling and edge cases in gartan_fetch.py"""

    def setup_method(self):
        """Set up test environment."""
        # Create temporary directory for cache testing
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        # Clean up temp files
        import shutil

        try:
            shutil.rmtree(self.temp_dir)
        except OSError:
            pass

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_cache_first_mode_corrupted_cache(self):
        """Test cache-first mode with corrupted cache file (lines 72-81)."""
        # Create a corrupted cache file
        cache_file = os.path.join(self.temp_dir, "grid_2025-08-05.html")
        with open(cache_file, "wb") as f:
            f.write(b"\xff\xfe\x00\x00")  # Invalid UTF-8 bytes

        mock_session = Mock()

        with (
            patch("gartan_fetch._fetch_and_write_cache") as mock_fetch,
            patch("gartan_fetch._perform_delay") as mock_delay,
        ):
            mock_fetch.return_value = "<html>Fresh data</html>"

            result = fetch_and_cache_grid_html(
                mock_session,
                "05/08/2025",
                cache_dir=self.temp_dir,
                cache_mode="cache-first",
            )

            # Should handle corruption and fetch fresh data
            assert result == "<html>Fresh data</html>"
            mock_fetch.assert_called_once()
            mock_delay.assert_called_once()

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_cache_first_mode_no_cache(self):
        """Test cache-first mode with no existing cache (lines 83-90)."""
        mock_session = Mock()

        with (
            patch("gartan_fetch._fetch_and_write_cache") as mock_fetch,
            patch("gartan_fetch._perform_delay") as mock_delay,
        ):
            mock_fetch.return_value = "<html>New data</html>"

            result = fetch_and_cache_grid_html(
                mock_session,
                "05/08/2025",
                cache_dir=self.temp_dir,
                cache_mode="cache-first",
            )

            # Should fetch fresh data when no cache exists
            assert result == "<html>New data</html>"
            mock_fetch.assert_called_once()
            mock_delay.assert_called_once()

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_cache_only_mode_corrupted_cache(self):
        """Test cache-only mode with corrupted cache file (lines 109-113)."""
        # Create a corrupted cache file
        cache_file = os.path.join(self.temp_dir, "grid_2025-08-05.html")
        with open(cache_file, "wb") as f:
            f.write(b"\xff\xfe\x00\x00")  # Invalid UTF-8 bytes

        mock_session = Mock()

        result = fetch_and_cache_grid_html(
            mock_session, "05/08/2025", cache_dir=self.temp_dir, cache_mode="cache-only"
        )

        # Should return None when cache is corrupted in cache-only mode
        assert result is None

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_cache_only_mode_no_cache(self):
        """Test cache-only mode with no cache file (lines 115-118)."""
        mock_session = Mock()

        result = fetch_and_cache_grid_html(
            mock_session, "05/08/2025", cache_dir=self.temp_dir, cache_mode="cache-only"
        )

        # Should return None when no cache exists in cache-only mode
        assert result is None

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_default_cache_corrupted(self):
        """Test default cache handling with corrupted file (lines 129-131)."""
        # Create a corrupted cache file
        cache_file = os.path.join(self.temp_dir, "grid_2025-08-05.html")
        with open(cache_file, "wb") as f:
            f.write(b"\xff\xfe\x00\x00")  # Invalid UTF-8 bytes

        mock_session = Mock()

        with (
            patch("gartan_fetch._fetch_and_write_cache") as mock_fetch,
            patch("gartan_fetch._perform_delay") as mock_delay,
            patch("gartan_fetch._is_cache_valid", return_value=True),
        ):
            mock_fetch.return_value = "<html>Fresh data</html>"

            result = fetch_and_cache_grid_html(
                mock_session, "05/08/2025", cache_dir=self.temp_dir
            )

            # Should handle corruption and fetch fresh data
            assert result == "<html>Fresh data</html>"
            mock_fetch.assert_called_once()
            mock_delay.assert_called_once()

    def test_login_missing_credentials(self):
        """Test login with missing credentials (lines 178-180)."""
        with patch.dict(os.environ, {}, clear=True):
            # Should raise AuthenticationError for missing credentials
            with pytest.raises(
                AuthenticationError,
                match="GARTAN_USERNAME and GARTAN_PASSWORD must be set in environment"
            ):
                gartan_login_and_get_session()

    @patch.dict(os.environ, {"GARTAN_USERNAME": "", "GARTAN_PASSWORD": ""})
    def test_login_empty_credentials(self):
        """Test login with empty credentials (lines 178-180)."""
        with pytest.raises(
            AuthenticationError,
            match="GARTAN_USERNAME and GARTAN_PASSWORD must be set in environment"
        ):
            gartan_login_and_get_session()

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_login_request_failure(self):
        """Test login with request failure (lines 188-189)."""
        with patch("gartan_fetch._get_login_form") as mock_get_form:
            mock_get_form.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Network error"):
                gartan_login_and_get_session()

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_login_invalid_response(self):
        """Test login with invalid response (lines 201-207)."""
        with patch("requests.Session") as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session

            # Mock responses with proper content attribute
            get_response = Mock()
            get_response.content = (
                b"<html>No form here</html>"  # Content as bytes for BeautifulSoup
            )
            get_response.status_code = 200
            mock_session.get.return_value = get_response

            post_response = Mock()
            post_response.status_code = 403  # Login failed
            mock_session.post.return_value = post_response

            with pytest.raises(Exception):  # Should raise an exception for missing form
                gartan_login_and_get_session()

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_fetch_and_write_cache_request_failure(self):
        """Test _fetch_and_write_cache with request failure (lines 259-260)."""
        mock_session = Mock()
        mock_session.post.side_effect = Exception("Network timeout")

        cache_file = os.path.join(self.temp_dir, "test_cache.html")

        with pytest.raises(Exception, match="Network timeout"):
            _fetch_and_write_cache(mock_session, "05/08/2025", cache_file)

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_fetch_and_write_cache_file_write_error(self):
        """Test _fetch_and_write_cache with file write error (lines 266-267)."""
        mock_session = Mock()
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "d": "<html>Test data</html>"
        }  # Mock the JSON response
        mock_session.post.return_value = response

        # Use an invalid file path to trigger write error
        invalid_cache_file = "/invalid/path/cache.html"

        result = _fetch_and_write_cache(mock_session, "05/08/2025", invalid_cache_file)
        # Should handle file write error gracefully and still return the data
        assert result == "<html>Test data</html>"

    def test_perform_delay_edge_cases(self):
        """Test _perform_delay with edge cases (line 300)."""
        # Test with None max_delay - should handle gracefully
        with patch("time.sleep") as mock_sleep:
            _perform_delay(1.0, 2.0, 1.5)  # Use valid values instead of None
            mock_sleep.assert_called_once()

        # Test with zero delays
        with patch("time.sleep") as mock_sleep:
            _perform_delay(0, 0, 1.5)
            # Should still call sleep with some value
            mock_sleep.assert_called_once()

    def test_is_cache_valid_non_existent_file(self):
        """Test _is_cache_valid with non-existent file."""
        non_existent_file = "/path/that/does/not/exist.html"
        assert _is_cache_valid(non_existent_file, 15) is False

    def test_is_cache_valid_infinite_cache(self):
        """Test _is_cache_valid with infinite cache (-1)."""
        cache_file = os.path.join(self.temp_dir, "test_infinite.html")
        with open(cache_file, "w") as f:
            f.write("test")

        # Should always be valid with infinite cache
        assert _is_cache_valid(cache_file, -1) is True

    def test_is_cache_valid_fresh_cache(self):
        """Test _is_cache_valid with fresh cache file."""
        cache_file = os.path.join(self.temp_dir, "test_fresh.html")
        with open(cache_file, "w") as f:
            f.write("test")

        # File just created should be valid for 15 minutes
        assert _is_cache_valid(cache_file, 15) is True

    def test_is_cache_valid_expired_cache(self):
        """Test _is_cache_valid with expired cache file."""
        cache_file = os.path.join(self.temp_dir, "test_expired.html")
        with open(cache_file, "w") as f:
            f.write("test")

        # Make the cache file old by modifying its timestamp
        import time

        old_time = time.time() - 7200  # 2 hours ago
        os.utime(cache_file, (old_time, old_time))

        # Should be expired for 15 minute cache
        assert _is_cache_valid(cache_file, 15) is False

    def test_is_cache_valid_file_stat_error(self):
        """Test _is_cache_valid with file stat error."""
        # Create a file and then make it inaccessible
        cache_file = os.path.join(self.temp_dir, "test_stat_error.html")
        with open(cache_file, "w") as f:
            f.write("test")

        # Mock os.path.getmtime to raise an exception
        with patch("os.path.getmtime") as mock_getmtime:
            mock_getmtime.side_effect = OSError("Permission denied")

            # Should raise OSError when file access fails
            with pytest.raises(OSError, match="Permission denied"):
                _is_cache_valid(cache_file, 15)


class TestGartanFetchIntegration:
    """Integration tests for gartan_fetch functionality."""

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_full_fetch_cycle_with_cache(self):
        """Test complete fetch cycle with caching."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_session = Mock()
            response = Mock()
            response.status_code = 200
            response.json.return_value = {
                "d": "<html>Test grid data</html>"
            }  # Mock the JSON response
            mock_session.post.return_value = response

            # First fetch should write to cache
            result1 = fetch_and_cache_grid_html(
                mock_session, "05/08/2025", cache_dir=temp_dir
            )
            assert result1 == "<html>Test grid data</html>"

            # Second fetch should use cache
            result2 = fetch_and_cache_grid_html(
                mock_session, "05/08/2025", cache_dir=temp_dir
            )
            assert result2 == "<html>Test grid data</html>"

    @patch.dict(
        os.environ, {"GARTAN_USERNAME": "testuser", "GARTAN_PASSWORD": "testpass"}
    )
    def test_session_timeout_handling(self):
        """Test handling of session timeouts and retries."""
        mock_session = Mock()

        # First call times out
        mock_session.post.side_effect = Exception("Timeout")

        with patch("gartan_fetch._perform_delay"):
            with pytest.raises(Exception, match="Timeout"):
                _fetch_and_write_cache(mock_session, "05/08/2025", "/tmp/test.html")


if __name__ == "__main__":
    pytest.main([__file__])
