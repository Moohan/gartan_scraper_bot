"""Main entry point for Gartan Scraper Bot."""

import concurrent.futures
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from cli import CliArgs, create_argument_parser
from config import config
from db_store import init_db, insert_appliance_availability, insert_crew_availability
from gartan_fetch import (
    fetch_and_cache_grid_html,
    fetch_grid_html_for_date,
    gartan_login_and_get_session,
)
from logging_config import get_logger, setup_logging
from parse_grid import (
    aggregate_appliance_availability,
    aggregate_crew_availability,
    parse_grid_html,
)
from utils import get_week_aligned_date_range, log_debug

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
    setup_logging(log_level=logging.DEBUG)

    # Parse and validate arguments
    parser = create_argument_parser()
    try:
        args = CliArgs.from_args(parser.parse_args())
    except ValueError as e:
        logger.error(f"Invalid arguments: {e}")
        exit(1)

    today = datetime.now()
    session = gartan_login_and_get_session()

    # Calculate week-aligned date range for weekly availability tracking
    start_date, effective_max_days = get_week_aligned_date_range(args.max_days)

    # Clean up old cache files if not using cache
    if args.cache_mode is None:
        cleanup_old_cache_files(config.cache_dir, today)

    day_offset = 0
    all_statuses_determined = False
    daily_crew_lists: List[List[Dict[str, Any]]] = []
    crew_list_agg: List[Dict[str, Any]] = []
    daily_appliance_lists: List[Dict[str, Any]] = []

    logger.info(f"Fetching {effective_max_days} days of availability (week-aligned)...")
    start_time = time.time()

    # Determine if we should reset the database
    reset = (
        os.environ.get("RESET_DB", "false").lower() == "true"
        or args.fresh_start
    )
    
    if args.fresh_start:
        logger.info("🔄 Fresh start requested - clearing database and forcing complete rescrape")
        # Override cache mode to ensure fresh data fetching
        args.cache_mode = "no-cache"
        
    db_conn = init_db(reset=reset)
    try:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=config.max_workers
        ) as executor:
            parse_futures = []
            booking_dates = []
            while not all_statuses_determined and day_offset < effective_max_days:
                booking_date = (start_date + timedelta(days=day_offset)).strftime(
                    "%d/%m/%Y"
                )
                logger.info(
                    f"Processing day {day_offset+1}/{effective_max_days}: {booking_date}"
                )

                # Get cache minutes from config based on actual date
                current_date = start_date + timedelta(days=day_offset)
                days_from_today = (current_date.date() - today.date()).days
                cache_minutes = config.get_cache_minutes(days_from_today)

                # Log cache strategy
                if cache_minutes == -1:
                    logger.debug(
                        f"Using infinite cache for historic date: {booking_date}"
                    )
                else:
                    logger.debug(
                        f"Cache duration for {booking_date}: {cache_minutes} minutes"
                    )

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
                eta = avg_per_day * (effective_max_days - (day_offset + 1))
                logger.info(
                    f"Progress: {day_offset+1}/{effective_max_days} days | ETA: {int(eta)}s"
                )
                day_offset += 1

            # Collect results as they complete
            for i, future in enumerate(concurrent.futures.as_completed(parse_futures)):
                try:
                    result = future.result()
                    crew_list = result.get("crew_availability", [])
                    appliance_obj = result.get("appliance_availability", {})
                    daily_crew_lists.append(crew_list)
                    daily_appliance_lists.append(appliance_obj)
                except Exception as e:
                    # Find the booking date corresponding to the failed future
                    failed_booking_date = "Unknown"
                    for j, f in enumerate(parse_futures):
                        if f == future:
                            failed_booking_date = booking_dates[j]
                            break
                    log_debug(
                        "error",
                        f"Failed to parse grid for {failed_booking_date}: {e}",
                    )

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
                    if (
                        len(parts) >= 3
                    ):  # Support both old format (3 parts) and new format (5 parts)
                        crew_id = parts[0]
                        display_name = parts[1]
                        phone = parts[2]
                        email = parts[3] if len(parts) > 3 else ""
                        position = parts[4] if len(parts) > 4 else ""
                        # Store enhanced contact info
                        contact_map[crew_id] = (
                            f"{display_name}|{phone}|{email}|{position}"
                        )
        from db_store import (
            insert_appliance_availability,
            insert_crew_availability,
            insert_crew_details,
        )

        insert_crew_details(crew_list_agg, contact_map, db_conn=db_conn)
        insert_crew_availability(crew_list_agg, db_conn=db_conn)
        print(
            f"Saved crew availability for {len(crew_list_agg)} crew members to gartan_availability.db"
        )
        log_debug(
            "ok",
            f"Saved crew availability for {len(crew_list_agg)} crew members to gartan_availability.db",
        )

        # Aggregate and store appliance availability in SQLite
        appliance_agg = aggregate_appliance_availability(
            daily_appliance_lists, crew_list_agg
        )
        # Convert list of dicts to a single dict keyed by appliance name
        appliance_agg_dict = {
            item["appliance"]: item for item in appliance_agg if "appliance" in item
        }
        insert_appliance_availability(appliance_agg_dict, db_conn=db_conn)
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
            crew["name"]
            for crew in crew_list_agg
            if crew.get("available_for") == ">72h"
        ]
        if all_statuses_determined:
            logger.info(
                f"All upcoming crew availability determined after {day_offset} days."
            )
        elif undetermined:
            logger.warning(
                f"Could not get all upcoming availability after searching {effective_max_days} days "
                f"for crew members: {', '.join(undetermined)}"
            )
        elif got_72h:
            logger.info(
                f"Got at least 72 hours availability for crew after searching {day_offset} days: "
                f"{', '.join(got_72h)}"
            )
    finally:
        if db_conn:
            db_conn.close()
