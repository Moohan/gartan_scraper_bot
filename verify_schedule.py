"""
Verifies the calculated schedule data against the real-time station display.
"""

import json
import logging
from datetime import datetime

import requests

from api_server import get_crew_available_data, get_crew_list_data


def setup_logging():
    """Sets up logging for the verification tool."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("discrepancy.log"),
            logging.StreamHandler(),
        ],
    )


def get_real_time_data():
    """Fetches the real-time data from the API."""
    try:
        response = requests.get("http://localhost:5000/station/now")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching real-time data: {e}")
        return None


def get_calculated_data():
    """Fetches the calculated data from the API."""
    try:
        crew_list = get_crew_list_data()
        available_crew = []
        for crew in crew_list:
            availability = get_crew_available_data(crew["id"])
            if availability.get("available"):
                available_crew.append(crew)
        return available_crew
    except Exception as e:
        logging.error(f"Error fetching calculated data: {e}")
        return None


def compare_data(real_time_data, calculated_data):
    """Compares the real-time data with the calculated data."""
    if not real_time_data or not calculated_data:
        logging.error("One of the data sources is unavailable for comparison.")
        return

    real_time_crew = {crew["name"] for crew in real_time_data["available_firefighters"]}
    calculated_crew = {crew["name"] for crew in calculated_data}

    discrepancies = []

    # Find crew in real-time data but not in calculated data
    for crew_name in real_time_crew - calculated_crew:
        discrepancies.append(
            f"'{crew_name}' is present in real-time data but not in calculated data."
        )

    # Find crew in calculated data but not in real-time data
    for crew_name in calculated_crew - real_time_crew:
        discrepancies.append(
            f"'{crew_name}' is present in calculated data but not in real-time data."
        )

    if discrepancies:
        logging.warning("Discrepancies found between real-time and calculated data:")
        for discrepancy in discrepancies:
            logging.warning(discrepancy)
    else:
        logging.info("No discrepancies found between real-time and calculated data.")


if __name__ == "__main__":
    setup_logging()
    logging.info("Starting schedule verification.")

    real_time_data = get_real_time_data()
    calculated_data = get_calculated_data()

    compare_data(real_time_data, calculated_data)

    logging.info("Schedule verification finished.")
