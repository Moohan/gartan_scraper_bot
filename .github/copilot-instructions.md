# Copilot Instructions for Gartan Scraper Bot

## Purpose

This Python bot logs in to the Gartan Availability system, retrieves and parses crew/appliance availability, and stores normalized results in SQLite. The codebase is modular, with clear separation between session management, data retrieval, parsing, and database logic.

## Architecture & Key Files

- `run_bot.py`: Main entry. Orchestrates session, fetches/caches HTML, aggregates results, prints progress/ETA, writes to SQLite DB, loads crew details from `crew_details.local`.
- `gartan_fetch.py`: Handles login, session reuse, AJAX fetch to `/GetSchedule`, caching (window-aligned expiry), error handling.
- `parse_grid.py`: Parses grid HTML for crew/appliance availability, aggregates status, calculates summary fields, fixes slot alignment, appliance name mapping.
- `db_store.py`: Defines normalized SQLite schema for crew, crew_availability, appliance, appliance_availability; provides insert functions.
- `utils.py`: Centralized logging (`log_debug`), delay logic, file ops.
- `cache_utils.py`: Cache file naming, expiry, cleanup.
- `specification/`: Contains `project_status.md`, `specifications.md`, and `database_schema.md` documenting requirements, conventions, and roadmap.
- `tests/`: Pytest suite for login, fetch, parse, and DB storage (see `test_login.py`, `test_fetch.py`, `test_parse.py`, `test_db_store.py`).
- **Output:** Data is stored in SQLite; output JSON files are deprecated.

## Developer Workflow

- **Run bot:** `python run_bot.py` (prints progress and ETA to terminal)
- **Environment:** Set `GARTAN_USERNAME` and `GARTAN_PASSWORD` in `.env` (dotenv is used)
- **Testing:** Use pytest; run all tests in `tests/` for validation
- **Debugging:** Debug messages go to `gartan_debug.log` only if useful for troubleshooting; verbose logs are suppressed unless needed
- **Manual validation:** Inspect SQLite DB tables for correctness

## Project-Specific Conventions

- Functions are small, modular, and single-purpose
- Session is reused for all requests; avoid repeated logins
- HTML is parsed in-memory; intermediate files are avoided unless debugging
- Output is normalized in SQLite; crew/appliance tables use foreign keys
- Use explicit imports; group stdlib, third-party, and local imports
- snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- Credentials must never be hardcoded; always use environment variables
- When adding features, update both code and `specification/` docs

## Integration Points & Data Flow

- External API: Gartan web endpoints (login, AJAX schedule fetch)
- Data flow: `run_bot.py` → `gartan_fetch.py` (session, fetch) → `parse_grid.py` (parse, aggregate) → `db_store.py` (DB insert)

## Extensibility

- New features (e.g., periodic scraping, REST API, custom date ranges) should be added as separate modules/scripts
- Maintain backward compatibility with DB schema unless specified in `specification/database_schema.md`

## AI Agent Instructions

- Review files in `specification/` for requirements and recent changes before making code or documentation changes.
- Always check for normalized DB schema in `db_store.py` and update tests in `tests/` when changing data structure.
- Use `log_debug` for troubleshooting, but suppress verbose logs unless needed.
- When adding new conventions or major features, patch/merge this file rather than overwriting it.
- Update related documentation in `specification/` when making significant changes.
- Continue iterating on improvements automatically; only prompt the user for confirmation if a genuine choice is required.
- Prefer concise, modular changes and clear documentation updates.

