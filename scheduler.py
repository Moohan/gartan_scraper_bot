#!/usr/bin/env python3
"""
Background scheduler for periodic data collection

Runs the Gartan scraper every 5 minutes using intelligent cache rules
"""

import logging
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import schedule

from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DB_PATH = config.db_path


def check_database_health() -> bool:
    """Check if database exists and has recent data"""
    try:
        if not os.path.exists(DB_PATH):
            logger.warning("Database does not exist")
            return False

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if we have crew data
        cursor.execute("SELECT COUNT(*) FROM crew")
        crew_count = cursor.fetchone()[0]

        if crew_count == 0:
            logger.warning("No crew data in database")
            conn.close()
            return False

        # Check if we have recent availability data
        cursor.execute(
            """
            SELECT COUNT(*) FROM crew_availability 
            WHERE datetime(end_time) > datetime('now', '-1 day')
        """
        )
        recent_blocks = cursor.fetchone()[0]

        conn.close()

        logger.info(
            f"Database health: {crew_count} crew, {recent_blocks} recent blocks"
        )
        return recent_blocks > 0

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def run_scraper(max_days: int = 3) -> bool:
    """Run the scraper with specified parameters"""
    try:
        logger.info(f"Starting scraper run for {max_days} days")

        # Use cache-first mode for efficiency in production
        cmd = [
            sys.executable,
            "run_bot.py",
            "--max-days",
            str(max_days),
        ]

        # Run the scraper
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            logger.info("Scraper run completed successfully")
            logger.debug(f"Scraper output: {result.stdout}")
            return True
        else:
            logger.error(f"Scraper failed with return code {result.returncode}")
            logger.error(f"Scraper stderr: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("Scraper run timed out after 5 minutes")
        return False
    except Exception as e:
        logger.error(f"Error running scraper: {e}")
        return False


def scheduled_scrape():
    """Scheduled scraper run with intelligent parameters"""
    logger.info("=" * 50)
    logger.info("Starting scheduled scrape")

    # Check current database health
    db_healthy = check_database_health()

    # Determine scraper parameters based on database state
    if not db_healthy:
        # If no recent data, do a more comprehensive scrape
        max_days = 7
        logger.info("No recent data - performing comprehensive scrape")
    else:
        # If database is healthy, do a minimal update
        max_days = 3
        logger.info("Database healthy - performing update scrape")

    # Run the scraper
    success = run_scraper(max_days)

    if success:
        # Verify the update worked
        new_health = check_database_health()
        if new_health:
            logger.info("Scheduled scrape completed successfully")
        else:
            logger.warning("Scrape completed but database health check failed")
    else:
        logger.error("Scheduled scrape failed")

    logger.info("Scheduled scrape finished")
    logger.info("=" * 50)


def initial_data_check():
    """Check if we need to do an initial scrape on startup"""
    logger.info("Performing initial data check...")

    if not check_database_health():
        logger.info("No valid data found - performing initial scrape")
        success = run_scraper(7)  # Get a week of data initially

        if success:
            logger.info("Initial scrape completed")
        else:
            logger.error("Initial scrape failed - will retry on next scheduled run")
    else:
        logger.info("Database contains valid data - skipping initial scrape")


def main():
    """Main scheduler loop"""
    logger.info("🕒 Starting Gartan Scheduler")
    logger.info("Scheduling scraper to run every 5 minutes")

    # Perform initial data check
    initial_data_check()

    # Schedule the scraper to run every 5 minutes
    schedule.every(5).minutes.do(scheduled_scrape)

    # Also schedule a comprehensive daily scrape at 6 AM
    schedule.every().day.at("06:00").do(lambda: run_scraper(14))

    logger.info("Scheduler started - press Ctrl+C to stop")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds

    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise


if __name__ == "__main__":
    main()
