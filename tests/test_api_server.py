"""Integration tests for the API server."""
import os
import unittest
from unittest.mock import patch

from api_server import app


class TestApiServer(unittest.TestCase):
    """Test cases for the API server."""

    def setUp(self):
        """Set up the test client."""
        self.app = app.test_client()
        self.app.testing = True

    @patch("api_server.fetch_station_display_html")
    def test_get_station_now(self, mock_fetch):
        """Test the /station/now endpoint."""
        # Get the absolute path to the test file.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_file_path = os.path.join(current_dir, "station_display_sample.html")

        with open(test_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        mock_fetch.return_value = html_content

        response = self.app.get("/station/now")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {
                "time": "12:34:56",
                "date": "01/01/2025",
                "station": "P22 Dunkeld",
                "crewing_summary": {
                    "MGR": {"available": 1, "difference": 0},
                    "FFC": {"available": 2, "difference": 0},
                },
                "available_firefighters": [
                    {"role": "FFD", "name": "HAYES, JA", "skills": ["BA"]},
                    {"role": "FFC", "name": "SMITH, A", "skills": ["ERD", "BA"]},
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
