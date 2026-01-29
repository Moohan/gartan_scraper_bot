"""Main entry point for Gartan Scraper Bot."""

import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

from cli import CliArgs, create_argument_parser
from config import config
from db_store import (
    init_db,
    insert_appliance_availability,
    insert_crew_availability,
    insert_crew_details,
)
from gartan_fetch import (
    AuthenticationError,
    fetch_and_cache_grid_html,
    gartan_login_and_get_session,
)
from logging_config import get_logger, setup_logging
from parse_grid import (
    aggregate_appliance_availability,
    aggregate_crew_availability,
    parse_grid_html,
)
from utils import get_week_aligned_date_range

logger = get_logger()


def cleanup_old_cache_files(cache_dir: str, today: datetime) -> None:
    """Clean up cache files older than today."""
    if not os.path.exists(cache_dir):
        logger.debug(f"Cache directory {cache_dir} does not exist, skipping cleanup")
        return

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


def main():
    # Set up logging
    setup_logging(log_level=logging.DEBUG)

    # Parse and validate arguments
    parser = create_argument_parser()
    try:
        args = CliArgs.from_args(parser.parse_args())
    except ValueError as e:
        logger.error(f"Invalid arguments: {e}")
        sys.exit(1)

    today = datetime.now()

    # If running in cache-only mode, we skip authentication and proceed using only cached files.
    session = None
    if args.cache_mode != "cache-only":
        try:
            # Authenticate using the synchronous requests library
            session = gartan_login_and_get_session()
        except AuthenticationError as e:
            logger.warning(
                f"🔒 Authentication failed: {str(e)} — continuing without authenticated session"
            )
            session = None
        except Exception as e:
            logger.warning(
                f"⚠️ Unexpected error during login: {str(e)} — continuing without authenticated session"
            )
            session = None
    else:
        logger.info(
            "Running in cache-only mode: skipping authentication and network fetches."
        )

    if session is None and args.cache_mode != "cache-only":
        logger.error("🚫 No valid session and not in cache-only mode. Aborting scrape.")
        return  # Exit gracefully

    # Calculate week-aligned date range for weekly availability tracking
    start_date, effective_max_days = get_week_aligned_date_range(args.max_days)

    # Clean up old cache files if not using cache
    if args.cache_mode is None:
        cleanup_old_cache_files(config.cache_dir, today)

    daily_crew_lists: List[List[Dict[str, Any]]] = []
    daily_appliance_lists: List[Dict[str, Any]] = []

    logger.info(f"Fetching {effective_max_days} days of availability (week-aligned)...")
    start_time = time.time()

    # Determine if we should reset the database
    reset = os.environ.get("RESET_DB", "false").lower() == "true" or args.fresh_start

    if args.fresh_start:
        logger.info(
            "🔄 Fresh start requested - clearing database and forcing complete rescrape"
        )
        # Override cache mode to ensure fresh data fetching
        args.cache_mode = "no-cache"

    db_conn = init_db(reset=reset)
    try:
        booking_dates = [
            (start_date + timedelta(days=i)).strftime("%d/%m/%Y")
            for i in range(effective_max_days)
        ]

        for i, date in enumerate(booking_dates):
            logger.info(f"Processing day {i+1}/{effective_max_days}: {date}")

            days_from_today = (
                datetime.strptime(date, "%d/%m/%Y").date() - today.date()
            ).days
            cache_minutes = config.get_cache_minutes(days_from_today)

            # fetch_and_cache_grid_html handles cache logic internally
            html = fetch_and_cache_grid_html(
                session,
                date,
                cache_dir=config.cache_dir,
                cache_minutes=cache_minutes,
                cache_mode=args.cache_mode,
            )

            if html:
                try:
                    result = parse_grid_html(html, date)
                    crew_list = result.get("crew_availability", [])
                    appliance_obj = result.get("appliance_availability", {})
                    daily_crew_lists.append(crew_list)
                    daily_appliance_lists.append(appliance_obj)
                except Exception as exc:
                    logger.error(f"Error parsing data for {date}: {exc}")

            # Log progress
            elapsed = time.time() - start_time
            avg_per_day = elapsed / (i + 1)
            eta = avg_per_day * (len(booking_dates) - (i + 1))
            logger.info(f"Progress: {i+1}/{len(booking_dates)} days | ETA: {int(eta)}s")

        # All data is fetched and parsed, now process it
        crew_list_agg = aggregate_crew_availability(daily_crew_lists)

        insert_crew_details(crew_list_agg, db_conn=db_conn)
        insert_crew_availability(crew_list_agg, db_conn=db_conn)
        print(
            f"Saved crew availability for {len(crew_list_agg)} crew members to gartan_availability.db"
        )

        appliance_agg = aggregate_appliance_availability(daily_appliance_lists)
        appliance_agg_dict = {
            item["appliance"]: item for item in appliance_agg if "appliance" in item
        }
        insert_appliance_availability(appliance_agg_dict, db_conn=db_conn)
        print(
            f"Saved appliance availability for {len(appliance_agg)} appliances to gartan_availability.db"
        )

        # Final summary logging
        undetermined = [
            crew["name"]
            for crew in crew_list_agg
            if (
                (crew["next_available"] is None or crew["next_available_until"] is None)
                and crew.get("available_for") != ">72h"
            )
        ]
        if undetermined:
            logger.warning(
                f"Could not get all upcoming availability after searching {effective_max_days} days "
                f"for crew members: {', '.join(undetermined)}"
            )

    finally:
        if db_conn:
            db_conn.close()


if __name__ == "__main__":
    main()
