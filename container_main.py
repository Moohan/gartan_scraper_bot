#!/usr/bin/env python3
"""
Container orchestrator for Gartan Scraper Bot

Runs both the periodic scheduler and API server in a single container.
Starts the API server immediately to ensure port binding on hosting providers like Render.
"""

import logging
import os
import signal
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
        except Exception:
            logger.exception(f"Error terminating process {process.name}")

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
        # In a container, if the scheduler dies, we might want the whole container to restart
        os._exit(1)


def run_api_server():
    """Run the Flask API server process"""
    try:
        logger.info("Starting API server process")

        # Set environment variables for production
        os.environ["FLASK_DEBUG"] = "false"
        os.environ["PORT"] = os.environ.get("PORT", "5000")

        # Import and run the API server
        from api_server import app

        port = int(os.environ.get("PORT", 5000))
        # Use a proper production WSGI server if possible, but keep compatibility with current setup
        app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

    except Exception as e:
        logger.error(f"API server process failed: {e}")
        os._exit(1)


def main():
    """Main orchestrator"""
    logger.info("🚀 Starting Gartan Scraper Bot Container")

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Start the API server process FIRST and IMMEDIATELY
        # This ensures that hosting providers (like Render) see the port binding and mark the deploy as successful
        api_process = Process(target=run_api_server, name="api_server")
        api_process.daemon = True
        api_process.start()
        processes.append(api_process)
        logger.info("API server process started (immediate bind)")

        # Start the scheduler process
        scheduler_process = Process(target=run_scheduler, name="scheduler")
        scheduler_process.daemon = True
        scheduler_process.start()
        processes.append(scheduler_process)
        logger.info("Scheduler process started")

        # Monitor processes
        logger.info("All processes started - monitoring health")

        while not shutdown_flag.is_set():
            # Check if processes are still running
            for process in processes:
                if not process.is_alive():
                    logger.error(
                        f"Process {process.name} died unexpectedly (exit code: {process.exitcode})"
                    )
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
