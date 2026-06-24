# Local Usage Guide

This guide is intended for users who want to run the Gartan Scraper Bot on their local machine for testing, development, or one-off data fetching.

## Prerequisites

1. **Python 3.13+** installed on your system.
2. **Valid Gartan Credentials**.

## Initial Setup

1. **Clone the Repository** and navigate to the root directory:

    ```bash
    git clone <repository_url>
    cd gartan_scraper_bot
    ```

2. **Create a Virtual Environment** and install dependencies:

    ```bash
    python -m venv .venv
    # Reactivate the environment depending on your OS (e.g., .venv\Scripts\activate on Windows)
    pip install -r requirements.txt
    ```

3. **Configure Credentials**:
    Create a `.env` file in the root directory with your Gartan credentials:

    ```bash
    GARTAN_USERNAME=your_username
    GARTAN_PASSWORD=your_password
    ```

## Running the Bot Locally

The main entry point for fetching data locally is `run_bot.py`. It handles fetching availability data, parsing it, and saving it to the SQLite database (`gartan_availability.db`).

Note: `run_bot.py` does not start the web API server. To serve the API, run `python api_server.py` after the database is populated.

### Common Commands

**1. Standard Run (Fetch Data)**:

```bash
python run_bot.py
```

This will fetch the latest 7 days of data (using cached files if available and fresh) and populate the SQLite database `gartan_availability.db`.

**2. Fresh Start (Clear DB and Rescrape)**:
If you want to ensure your local database represents the absolute latest source of truth without any cached data corruption:

```bash
python run_bot.py --fresh-start --max-days 7
```

**3. Cache Control**:
You can control how the bot uses cached HTML pages (saved in the `_cache/` directory):

```bash
# Force fresh fetch from the live Gartan system, ignoring cache:
python run_bot.py --no-cache --max-days 3

# Use cached files when available, only fetch missing days:
python run_bot.py --cache-first --max-days 3

# Offline testing (only parse locally cached files, do not connect to Gartan):
python run_bot.py --cache-only --max-days 3
```

### Starting the API

If your database (`gartan_availability.db`) is already populated and you want to serve the REST API:

```bash
python api_server.py
```

The API will be available at `http://localhost:5000/v1/`.

## Exploring Data

For debugging parsing issues or exploring specific Excel outputs from Gartan, you can use the interactive scripts in the `scripts/` folder:

- `python scripts/explore_excel.py`
- `python scripts/validate_excel.py`

## Viewing Logs

Logs are written to the `logs/` directory (e.g., `logs/gartan_api.json`) and the console. To enable detailed debugging output in `run_bot.py`, append `--debug` to your command.
