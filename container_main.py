#!/usr/bin/env python3
"""
Container orchestrator for Gartan Scraper Bot

Runs both the periodic scheduler and API server in a single container
"""

import logging
import os
import signal
import subprocess
import sys
import threading
import time
from multiprocessing import Process

from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize configuration
config = Config()

# Global process tracking
processes = []
shutdown_flag = threading.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum} - initiating graceful shutdown")
    shutdown_flag.set()

    # Terminate all processes
    for process in processes:
        try:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
                if process.is_alive():
                    logger.warning(
                        f"Process {process.name} did not terminate gracefully"
                    )
                    process.kill()
        except Exception as e:
            logger.error(f"Error terminating process {process.name}: {e}")

    logger.info("Shutdown complete")
    sys.exit(0)


def run_scheduler():
    """Run the periodic scheduler process"""
    try:
        logger.info("Starting scheduler process")
        from scheduler import main as scheduler_main

        scheduler_main()
    except Exception as e:
        logger.error(f"Scheduler process failed: {e}")
        raise


def run_api_server():
    """Run the Flask API server process using Gunicorn in production"""
    try:
        logger.info("Starting API server process")

        # Set environment variables for production
        os.environ["FLASK_DEBUG"] = "false"
        port_str = os.environ.get("PORT", "5000")

        # Validate port to prevent command injection
        if not port_str.isdigit():
            logger.error(f"Invalid PORT: {port_str}")
            sys.exit(1)

        # Use gunicorn for production as recommended for security
        # We use subprocess.run with a list to avoid shell=True.
        # Inline the command list and use shell=False for maximum security and to satisfy static analysis.
        logger.info(f"Launching Gunicorn on port {port_str}")
        subprocess.run(
            [
                "gunicorn",
                "--bind",
                f"0.0.0.0:{port_str}",
                "--workers",
                "4",
                "--timeout",
                "120",
                "api_server:app",
            ],
            check=True,
            shell=False,
        )  # nosec B603 B607

    except Exception as e:
        logger.error(f"API server process failed: {e}")
        raise


def wait_for_database():
    """Wait for initial database to be populated"""
    import sqlite3

    max_wait = 300  # 5 minutes
    wait_time = 0

    while wait_time < max_wait and not shutdown_flag.is_set():
        try:
            if os.path.exists(config.db_path):
                conn = sqlite3.connect(config.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM crew")
                crew_count = cursor.fetchone()[0]
                conn.close()

                if crew_count > 0:
                    logger.info(f"Database ready with {crew_count} crew members")
                    return True

            logger.info(f"Waiting for database... ({wait_time}s/{max_wait}s)")
            time.sleep(10)
            wait_time += 10

        except Exception as e:
            logger.debug(f"Database check failed: {e}")
            time.sleep(10)
            wait_time += 10

    logger.warning("Database not ready after maximum wait time")
    return False


def main():
    """Main orchestrator"""
    logger.info("🚀 Starting Gartan Scraper Bot Container")

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start the scheduler process
        scheduler_process = Process(target=run_scheduler, name="scheduler")
        scheduler_process.start()
        processes.append(scheduler_process)
        logger.info("Scheduler process started")

        # Wait for database to be populated
        logger.info("Waiting for initial data...")
        if wait_for_database():
            logger.info("Database ready - starting API server")
        else:
            logger.warning("Starting API server without confirmed database")

        # Start the API server process
        api_process = Process(target=run_api_server, name="api_server")
        api_process.start()
        processes.append(api_process)
        logger.info("API server process started")

        # Monitor processes
        logger.info("All processes started - monitoring health")

        while not shutdown_flag.is_set():
            # Check if processes are still running
            for process in processes:
                if not process.is_alive():
                    logger.error(f"Process {process.name} died unexpectedly")
                    # In production, you might want to restart the process
                    # For now, we'll trigger a shutdown
                    shutdown_flag.set()
                    break

            time.sleep(30)  # Check every 30 seconds

    except Exception as e:
        logger.error(f"Orchestrator error: {e}")
        shutdown_flag.set()

    # Cleanup
    signal_handler(signal.SIGTERM, None)


if __name__ == "__main__":
    main()
