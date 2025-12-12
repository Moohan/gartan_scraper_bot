import logging
import unittest
from unittest.mock import MagicMock

from station_feed_verification import compare_and_log_discrepancies


class TestStationFeedVerification(unittest.TestCase):

    def test_compare_and_log_discrepancies(self):
        # Create a mock logger
        mock_logger = MagicMock(spec=logging.Logger)

        # Test data with a discrepancy
        station_feed_data = {"P22P6": {"availability": True}}
        calculated_states = {"P22P6": {"available_now": False}}

        # Call the function
        compare_and_log_discrepancies(station_feed_data, calculated_states, mock_logger)

        # Assert that the logger was called with a message indicating the discrepancy
        mock_logger.info.assert_called_once()
        self.assertIn(
            "station feed showed P22P6 as available, but the calculated state was unavailable",
            mock_logger.info.call_args[0][0],
        )

        # Reset the mock logger
        mock_logger.reset_mock()

        # Test data with no discrepancy
        station_feed_data = {"P22P6": {"availability": True}}
        calculated_states = {"P22P6": {"available_now": True}}

        # Call the function
        compare_and_log_discrepancies(station_feed_data, calculated_states, mock_logger)

        # Assert that the logger was not called
        mock_logger.info.assert_not_called()

    def test_appliance_not_in_calculated_states(self):
        """Test that appliances only in station feed don't cause errors."""
        mock_logger = MagicMock(spec=logging.Logger)
        station_feed_data = {
            "P22P6": {"availability": True},
            "P22P7": {"availability": False},
        }
        calculated_states = {"P22P6": {"available_now": True}}
        compare_and_log_discrepancies(station_feed_data, calculated_states, mock_logger)
        mock_logger.info.assert_not_called()

    def test_empty_inputs(self):
        """Test with empty dictionaries as input."""
        mock_logger = MagicMock(spec=logging.Logger)
        compare_and_log_discrepancies({}, {}, mock_logger)
        mock_logger.info.assert_not_called()

    def test_multiple_appliances_mixed_results(self):
        """Test with multiple appliances, some with discrepancies."""
        mock_logger = MagicMock(spec=logging.Logger)
        station_feed_data = {
            "P22P6": {"availability": True},
            "P22P7": {"availability": False},
        }
        calculated_states = {
            "P22P6": {"available_now": False},  # Discrepancy
            "P22P7": {"available_now": False},  # Match
        }
        compare_and_log_discrepancies(station_feed_data, calculated_states, mock_logger)
        mock_logger.info.assert_called_once()
        self.assertIn("P22P6", mock_logger.info.call_args[0][0])
        self.assertNotIn("P22P7", mock_logger.info.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
