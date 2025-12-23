"""Main entry point for Gartan Scraper Bot."""

import asyncio
import concurrent.futures
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import aiohttp

from async_gartan_fetch import fetch_grid_html_for_date_async
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
    fetch_station_feed_html,
    gartan_login_and_get_session,
)
from logging_config import get_logger, setup_logging
from parse_grid import (
    aggregate_appliance_availability,
    aggregate_crew_availability,
    parse_grid_html,
    parse_station_feed_html,
)
from station_feed_verification import (
    compare_and_log_discrepancies,
    setup_verification_logger,
)
from utils import get_week_aligned_date_range, log_debug

logger = get_logger()


def read_crew_details_file() -> Dict[str, str]:
    """Reads and parses the crew_details.local file."""
    contact_map = {}
    if os.path.exists("crew_details.local"):
        with open("crew_details.local", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|")
                if len(parts) >= 3:
                    crew_id, display_name, phone = parts[0], parts[1], parts[2]
                    email = parts[3] if len(parts) > 3 else ""
                    position = parts[4] if len(parts) > 4 else ""
                    contact_map[crew_id] = f"{display_name}|{phone}|{email}|{position}"
    return contact_map


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


def _is_cache_valid(cache_file: str, cache_minutes: int) -> bool:
    """
    Check if the cache file exists and is not expired.
    """
    if not os.path.exists(cache_file):
        return False

    if cache_minutes == -1:
        return True

    mtime = os.path.getmtime(cache_file)
    if (
        datetime.now() - datetime.fromtimestamp(mtime)
    ).total_seconds() / 60 < cache_minutes:
        return True
    return False


async def main():
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
    try:
        # Authenticate using the synchronous requests library
        session = gartan_login_and_get_session()
    except AuthenticationError as e:
        logger.error(f"🔒 Authentication failed: {str(e)}")
        logger.error("Please update your Gartan credentials and try again.")
        exit(1)
    except Exception as e:
        logger.error(f"⚠️ Unexpected error during login: {str(e)}")
        exit(1)

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
        # Bolt ⚡: Using asyncio to fetch all days of availability concurrently,
        # which is much faster than the previous sequential approach.
        # A semaphore is used to limit the number of concurrent requests to 10.
        cookies = session.cookies.get_dict()
        semaphore = asyncio.Semaphore(10)

        async with aiohttp.ClientSession(cookies=cookies) as aio_session:
            booking_dates = [
                (start_date + timedelta(days=i)).strftime("%d/%m/%Y")
                for i in range(effective_max_days)
            ]

            grid_htmls = [""] * len(booking_dates)
            fetch_tasks = []

            async def fetch_and_cache(date, index):
                async with semaphore:
                    logger.info(
                        f"Processing day {index+1}/{effective_max_days}: {date}"
                    )
                    cache_file = os.path.join(
                        config.cache_dir, f"grid_{date.replace('/', '-')}.html"
                    )
                    days_from_today = (
                        datetime.strptime(date, "%d/%m/%Y").date() - today.date()
                    ).days
                    cache_minutes = config.get_cache_minutes(days_from_today)

                    if args.cache_mode != "no-cache" and _is_cache_valid(
                        cache_file, cache_minutes
                    ):
                        logger.debug(f"Using cached data for {date}")
                        with open(cache_file, "r", encoding="utf-8") as f:
                            grid_htmls[index] = f.read()
                    else:
                        logger.debug(f"Fetching data for {date}")
                        html = await fetch_grid_html_for_date_async(aio_session, date)
                        if html:
                            grid_htmls[index] = html
                            with open(cache_file, "w", encoding="utf-8") as f:
                                f.write(html)

            for i, date in enumerate(booking_dates):
                task = fetch_and_cache(date, i)
                fetch_tasks.append(task)

            # Run all fetching tasks concurrently
            await asyncio.gather(*fetch_tasks)

            # Use a ThreadPoolExecutor for the CPU-bound parsing task
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=config.max_workers
            ) as executor:
                parse_futures = {
                    executor.submit(parse_grid_html, html, date): date
                    for html, date in zip(grid_htmls, booking_dates)
                    if html
                }

                for i, future in enumerate(
                    concurrent.futures.as_completed(parse_futures)
                ):
                    date = parse_futures[future]
                    try:
                        result = future.result()
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
                    logger.info(
                        f"Progress: {i+1}/{len(booking_dates)} days | ETA: {int(eta)}s"
                    )

        # All data is fetched and parsed, now process it
        crew_list_agg = aggregate_crew_availability(daily_crew_lists)

        contact_map = await asyncio.to_thread(read_crew_details_file)

        insert_crew_details(crew_list_agg, contact_map, db_conn=db_conn)
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

        # Station feed verification
        verification_logger = setup_verification_logger()
        station_feed_html = fetch_station_feed_html(session)
        if station_feed_html:
            station_feed_data = parse_station_feed_html(station_feed_html)
            if station_feed_data:
                compare_and_log_discrepancies(
                    station_feed_data, appliance_agg_dict, verification_logger
                )
                logger.info("Station feed verification completed successfully.")
            else:
                logger.warning("Could not parse station feed data for verification.")
        else:
            logger.warning("Could not fetch station feed for verification.")

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
    asyncio.run(main())
