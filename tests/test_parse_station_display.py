"""Unit tests for the parse_station_display module."""

import os
import unittest

from parse_station_display import parse_station_display_html


class TestParseStationDisplay(unittest.TestCase):
    """Test cases for the parse_station_display module."""

    def test_parse_station_display_html(self):
        """Test parsing of the station display HTML."""
        # Get the absolute path to the test file.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_file_path = os.path.join(current_dir, "station_display_sample.html")

        with open(test_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        parsed_data = parse_station_display_html(html_content)

        self.assertIsNotNone(parsed_data)
        self.assertEqual(parsed_data["time"], "12:34:56")
        self.assertEqual(parsed_data["date"], "01/01/2025")
        self.assertEqual(parsed_data["station"], "P22 Dunkeld")
        self.assertEqual(
            parsed_data["crewing_summary"],
            {
                "MGR": {"available": 1, "difference": 0},
                "FFC": {"available": 2, "difference": 0},
            },
        )
        self.assertEqual(
            parsed_data["available_firefighters"],
            [
                {"role": "FFD", "name": "HAYES, JA", "skills": ["BA"]},
                {"role": "FFC", "name": "SMITH, A", "skills": ["ERD", "BA"]},
            ],
        )


if __name__ == "__main__":
    unittest.main()
