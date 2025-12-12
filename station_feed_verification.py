import logging
from datetime import datetime


def setup_verification_logger():
    """Sets up a logger for station feed verification."""
    logger = logging.getLogger("station_feed_verification")
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler("station_feed_verification.log")
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger


def compare_and_log_discrepancies(
    station_feed_data: dict, calculated_states: dict, logger: logging.Logger
) -> None:
    """
    Compares station feed data with calculated states and logs discrepancies.

    Args:
        station_feed_data (dict): Parsed data from the station feed.
        calculated_states (dict): Calculated states from the main schedule.
        logger (logging.Logger): The logger to use for logging discrepancies.
    """
    now = datetime.now().strftime("%H:%M:%S")

    # This is a placeholder for the actual comparison logic.
    # The data structures will be determined by the parsing functions.
    for appliance, feed_data in station_feed_data.items():
        if appliance in calculated_states:
            calculated_data = calculated_states[appliance]

            feed_availability = feed_data.get("availability")
            calculated_availability = calculated_data.get("available_now")

            if (
                feed_availability is not None
                and calculated_availability is not None
                and feed_availability != calculated_availability
            ):
                logger.info(
                    f"At {now} station feed showed {appliance} as {'available' if feed_availability else 'unavailable'}, "
                    f"but the calculated state was {'available' if calculated_availability else 'unavailable'}."
                )
