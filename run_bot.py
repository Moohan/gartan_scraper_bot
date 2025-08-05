"""Main entry point for Gartan Scraper Bot."""

from typing import Dict, List, Optional, Any
import os
import time
import random
from datetime import datetime, timedelta
import concurrent.futures
import re

from utils import log_debug
from gartan_fetch import (
    gartan_login_and_get_session,
    fetch_grid_html_for_date,
    fetch_and_cache_grid_html,
)
from parse_grid import (
    parse_grid_html,
    aggregate_crew_availability,
    aggregate_appliance_availability,
)
from db_store import init_db, insert_crew_availability, insert_appliance_availability
from config import config
from cli import create_argument_parser, CliArgs
from logging_config import setup_logging, get_logger

logger = get_logger()


def cleanup_old_cache_files(cache_dir: str, today: datetime) -> None:
    """Clean up cache files older than today."""
    for fname in os.listdir(cache_dir):
        match = re.match(r"grid_(\d{2}-\d{2}-\d{4})\.html", fname)
        if match:
            file_date_str = match.group(1)
            try:
                file_date = datetime.strptime(file_date_str, "%d-%m-%Y")
                if file_date < today.replace(hour=0, minute=0, second=0, microsecond=0):
                    os.remove(os.path.join(cache_dir, fname))
                    logger.info(f"Deleted old cache file: {fname}")
            except Exception as e:
                logger.warning(f"Failed to process cache file {fname}: {e}")


if __name__ == "__main__":
    # Set up logging
    setup_logging()

    # Parse and validate arguments
    parser = create_argument_parser()
    try:
        args = CliArgs.from_args(parser.parse_args())
    except ValueError as e:
        logger.error(f"Invalid arguments: {e}")
        exit(1)

    today = datetime.now()
    session = gartan_login_and_get_session()

    # Clean up old cache files if not using cache
    if args.cache_mode is None:
        cleanup_old_cache_files(config.cache_dir, today)

    day_offset = 0
    all_statuses_determined = False
    daily_crew_lists: List[List[Dict[str, Any]]] = []
    crew_list_agg: List[Dict[str, Any]] = []
    daily_appliance_lists: List[Dict[str, Any]] = []

    logger.info(f"Fetching up to {args.max_days} days of availability...")
    start_time = time.time()

    init_db()
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=config.max_workers
    ) as executor:
        parse_futures = []
        booking_dates = []
        while not all_statuses_determined and day_offset < args.max_days:
            booking_date = (today + timedelta(days=day_offset)).strftime("%d/%m/%Y")
            logger.info(
                f"Processing day {day_offset+1}/{args.max_days}: {booking_date}"
            )

            # Get cache minutes from config
            cache_minutes = config.get_cache_minutes(day_offset)

            grid_html = fetch_and_cache_grid_html(
                session,
                booking_date,
                cache_dir=config.cache_dir,
                cache_minutes=cache_minutes,
                min_delay=1,
                max_delay=10,
                base=1.5,
                cache_mode=args.cache_mode,
            )

            if not grid_html:
                logger.error(f"Failed to get grid HTML for {booking_date}.")
                day_offset += 1
                continue

            # Start parsing in background
            future = executor.submit(parse_grid_html, grid_html, booking_date)
            parse_futures.append(future)
            booking_dates.append(booking_date)

            # Calculate and display progress
            elapsed = time.time() - start_time
            avg_per_day = elapsed / (day_offset + 1)
            eta = avg_per_day * (args.max_days - (day_offset + 1))
            logger.info(
                f"Progress: {day_offset+1}/{args.max_days} days | ETA: {int(eta)}s"
            )
            day_offset += 1

        # Collect results as they complete
        for i, future in enumerate(parse_futures):
            try:
                result = future.result()
                crew_list = result.get("crew_availability", [])
                appliance_obj = result.get("appliance_availability", {})
                daily_crew_lists.append(crew_list)
                daily_appliance_lists.append(appliance_obj)
            except Exception as e:
                log_debug("error", f"Failed to parse grid for {booking_dates[i]}: {e}")

        crew_list_agg = aggregate_crew_availability(daily_crew_lists)
        all_statuses_determined = all(
            (
                crew["next_available"] is not None
                and crew["next_available_until"] is not None
            )
            for crew in crew_list_agg
        )

    # Read crew contact info from crew_details.local
    contact_map = {}
    if os.path.exists("crew_details.local"):
        with open("crew_details.local", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|")
                if len(parts) == 3:
                    crew_id, display_name, phone = parts
                    contact_map[crew_id] = f"{display_name}|{phone}"
    from db_store import insert_crew_details

    insert_crew_details(crew_list_agg, contact_map)
    insert_crew_availability(crew_list_agg)
    print(
        f"Saved crew details and availability for {len(crew_list_agg)} crew members to gartan_availability.db"
    )
    log_debug(
        "ok",
        f"Saved crew details and availability for {len(crew_list_agg)} crew members to gartan_availability.db",
    )

    # Aggregate and store appliance availability in SQLite
    appliance_agg = aggregate_appliance_availability(
        daily_appliance_lists, crew_list_agg
    )
    # Insert appliance data with correct naming
    if isinstance(appliance_agg, list):
        for appliance_entry in appliance_agg:
            appliance_name = appliance_entry.get("appliance", "UNKNOWN")
            info = {k: v for k, v in appliance_entry.items() if k != "appliance"}
            insert_appliance_availability({appliance_name: info})
    else:
        insert_appliance_availability(appliance_agg)
    print(
        f"Saved appliance availability for {len(appliance_agg)} appliances to gartan_availability.db"
    )
    log_debug(
        "ok",
        f"Saved appliance availability for {len(appliance_agg)} appliances to gartan_availability.db",
    )

    undetermined = [
        crew["name"]
        for crew in crew_list_agg
        if (
            (crew["next_available"] is None or crew["next_available_until"] is None)
            and crew.get("available_for") != ">72h"
        )
    ]
    got_72h = [
        crew["name"] for crew in crew_list_agg if crew.get("available_for") == ">72h"
    ]
    if all_statuses_determined:
        logger.info(
            f"All upcoming crew availability determined after {day_offset} days."
        )
    elif undetermined:
        logger.warning(
            f"Could not get all upcoming availability after searching {args.max_days} days "
            f"for crew members: {', '.join(undetermined)}"
        )
    elif got_72h:
        logger.info(
            f"Got at least 72 hours availability for crew after searching {day_offset} days: "
            f"{', '.join(got_72h)}"
        )
