# LLM Context & Developer Guide

This document is intended for LLMs and developers working on the Gartan Scraper Bot. It provides essential context, architecture details, and background decisions to help you understand how the system works and how to modify it.

## Project Aims

The Gartan Scraper Bot automates the collection of availability data from the Gartan Availability system. It then provides a REST API to query the real-time and historical availability of crew members and appliances (fire engines).

Its main purposes are:

1. Provide a reliable, automated way to check who is available.
2. Calculate durations of availability and accumulated hours (daily/weekly).
3. Evaluate complex business rules (e.g., Appliance P22P6 is only available if at least 4 crew are available, including specific skilled crew members).

## Architecture Overview

The system consists of several interoperating components:

### 1. Data Collection (`gartan_fetch.py` & `parse_grid.py`)

- **`gartan_fetch.py`**: Handles authentication and fetches the raw HTML pages from the Gartan system. It uses `playwright` (headless browser) because the Gartan system heavily relies on client-side rendering and complex session management.
- **`parse_grid.py`**: Parses the HTML grids using `BeautifulSoup`. It extracts crew and appliance availability based on cell colors (e.g., empty cells mean crew are available, green cells mean appliances are available) and text content.

### 2. Data Storage (`db_store.py`)

- The project uses **SQLite** (`gartan_data.db`) for lightweight, persistent storage.
- Availability is stored as continuous time blocks (`start_time` to `end_time`) rather than individual 15-minute slots for efficiency.
- **Data Quality Protections**: To handle historical data corruption or overlapping scrapes, the data storage and API logic include functions like `merge_time_periods` to prevent double-counting of availability hours.

### 3. REST API (`api_server.py`)

- Built with **Flask**.
- Exposes JSON endpoints for crew lists, availability checks, duration calculations, and weekly hours.
- Evaluates appliance availability dynamically based on crew skills and numbers.

### 4. Scheduling (`scheduler.py` & `run_bot.py`)

- The bot can run periodically (e.g., every 5 minutes) via `scheduler.py` to keep the database constantly updated with the latest live data.
- `run_bot.py` is the main entry point, providing CLI flags to control caching and the depth of the scrape.

## Background Decisions & Context

- **Headless Browser (Playwright):** Raw HTTP requests (via `requests`) proved too brittle for logging into Gartan and navigating the grid due to dynamic JavaScript tokens and session handling. Playwright ensures reliable loading of the fully rendered DOM.
- **Continuous Time Blocks:** Storing data as `[start_time, end_time]` records simplifies duration calculation and reduces database size significantly compared to storing thousands of rows for every 15-minute interval.
- **API Quality Filters:** The database historically suffered from corrupted scraping runs that created physically impossible time spans (e.g., >24 hours available in one day). The API queries specifically filter out corrupted blocks (e.g., `(julianday(end_time) - julianday(start_time)) <= 1.0` and merge overlapping periods to ensure accurate reporting.

## Adding and Running Tests

The project uses `pytest` for unit and integration testing.

### Running Existing Tests

Tests are located in the `tests/` directory. You can run them locally using:

```bash
python -m pytest tests/ -v
```

To run tests with coverage:

```bash
python -m pytest tests/ -v --cov=. --cov-report=term
```

### Adding New Tests

1. Create a new file in the `tests/` directory named `test_<feature>.py`.
2. Use `pytest` fixtures for database connections and mocked HTML files.
3. For scraping logic, use mocked HTML snippets in `tests/` or inline strings rather than hitting the live Gartan system during tests to ensure fast and reliable CI runs.

## CI/CD

GitHub Actions are configured in `.github/workflows/`.

- `ci.yml`: Runs formatting (`black`, `isort`), linting (`flake8`, `mypy`), tests (`pytest`), and automatically builds and pushes multi-platform Docker images to Docker Hub on merge to `main` or tag creation.
