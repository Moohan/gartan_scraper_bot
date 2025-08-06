# Copilot Instructions for Gartan Scraper Bot

## Purpose

This Python bot logs in to the Gartan Availability system, retrieves and parses crew/appliance availability, stores normalized results in SQLite, and exposes data via REST API. The codebase is highly modular with clear separation between scraping, parsing, storage, and API layers.

## Architecture & Key Files

### Core Scraping Engine
- `run_bot.py`: Main orchestrator. Handles multi-threaded fetching, progress/ETA tracking, CLI args, logging setup.
- `gartan_fetch.py`: Session management, login, AJAX calls to `/GetSchedule`, intelligent caching with window-aligned expiry.
- `parse_grid.py`: HTML parsing with crew/appliance detection, slot-to-block conversion, availability aggregation.
- `db_store.py`: Normalized SQLite schema with foreign keys, block-based storage for efficient queries.

### Configuration & Infrastructure  
- `config.py`: Centralized settings with dataclass, cache expiry rules, environment variable access.
- `cli.py`: Argument parsing and validation with dataclass patterns.
- `logging_config.py`: Structured logging with file rotation, separate debug/console levels.
- `cache_utils.py`: Cache file naming, timestamp alignment, cleanup logic.

### API Layer
- `test_direct_api.py`: Core API logic as pure functions (no Flask dependency), timezone-aware duration calculations.
- `validate_api.py`: API validation framework testing specification compliance.
- `specification/api_specification.md`: REST API spec with single-purpose endpoints (boolean/string responses).
- **API Status**: Phase 1&2 complete (6 endpoints), Phase 3 pending (advanced queries).

### Documentation & Testing
- `specification/`: Project status, database schema, API docs, roadmap - **always check before changes**.
- `tests/`: Comprehensive pytest suite covering login, parsing, DB operations, API validation.
- **Output**: SQLite database with block-based availability storage; JSON files deprecated.

## Developer Workflow

### Primary Commands
- **Run scraper**: `python run_bot.py --max-days 7` (supports cache options: `--no-cache`, `--cache-first`)
- **API testing**: `python validate_api.py` (tests all endpoints without Flask server)
- **Database inspection**: `python check_db.py` (shows row counts and sample data)
- **Full test suite**: `pytest tests/` (comprehensive validation)

### Environment Setup
- **Credentials**: Set `GARTAN_USERNAME` and `GARTAN_PASSWORD` in `.env` (dotenv loaded automatically)
- **Python**: 3.13+ with type hints, uses dataclass patterns extensively
- **Dependencies**: requests, BeautifulSoup, sqlite3, pytest, Flask (for API server)

### Debugging Workflows
- **Parsing issues**: Check `gartan_debug.log` for slot detection and aggregation details
- **API validation**: Use `test_direct_api.py` functions directly to bypass Flask server issues  
- **Cache debugging**: Inspect `_cache/grid_*.html` files for raw HTML content
- **DB schema**: Use `check_schema.py` for temporary schema inspection

## Project-Specific Conventions

### Code Patterns
- **Dataclass configurations**: `config.py` (ScraperConfig), `cli.py` (CliArgs) - use dataclasses with validation
- **Function modularity**: Small, single-purpose functions with clear input/output contracts
- **Logging strategy**: Use `log_debug()` from utils.py; debug goes to file, info+ to console  
- **Session reuse**: `gartan_fetch.py` maintains persistent session; avoid repeated logins
- **Cache intelligence**: Window-aligned expiry (15min today, 1hr tomorrow, 6hr+ beyond)

### Data Flow Conventions
- **HTML → Blocks**: Raw slots converted to continuous availability blocks in `parse_grid.py`
- **Foreign keys**: Database uses normalized schema; crew/appliance tables reference base entities
- **Timezone handling**: All database times are UTC; API calculations use timezone-aware datetime
- **Empty cell logic**: For crew, no background-color = available; for appliances, different logic applies

### API Design Patterns
- **Single-purpose endpoints**: Each endpoint returns one data type (boolean, string, JSON array)
- **Direct function testing**: `test_direct_api.py` bypasses Flask for pure logic validation
- **Specification-driven**: All API responses match `api_specification.md` format exactly
- **Error handling**: 404 for invalid IDs, proper JSON error responses

## Integration Points & Data Flow

### External Dependencies
- **Gartan web system**: Login endpoint, AJAX `/GetSchedule` calls, session-based authentication
- **Database**: SQLite with normalized schema, foreign key constraints enabled
- **Environment**: `.env` file for credentials, `crew_details.local` for contact info
- **Cache layer**: Filesystem cache in `_cache/` with intelligent expiry policies

### Critical Data Transformations
1. **Raw HTML** → `parse_grid.py` → **Crew/appliance availability dicts**
2. **Availability dicts** → `db_store.py` → **Continuous time blocks** (slot aggregation)
3. **Time blocks** → `test_direct_api.py` → **API responses** (duration calculations)

### Testing Architecture
- **Unit tests**: `tests/` directory with pytest, mocks external API calls
- **API validation**: `validate_api.py` tests actual database with real scraped data
- **Direct function testing**: Bypass Flask server issues by testing core logic functions
- **Specification compliance**: Automated verification that responses match `api_specification.md`

## Extensibility

- New features (e.g., periodic scraping, custom date ranges) should be added as separate modules/scripts
- Maintain backward compatibility with DB schema unless specified in `specification/database_schema.md`

## AI Agent Instructions

- Review files in `specification/` for requirements and recent changes before making code or documentation changes.
- Always check for normalized DB schema in `db_store.py` and update tests in `tests/` when changing data structure.
- Use `log_debug` for troubleshooting, but suppress verbose logs unless needed.
- When adding new conventions or major features, patch/merge this file rather than overwriting it.
- Update related documentation in `specification/` when making significant changes.
- Continue iterating on improvements automatically; only prompt the user for confirmation if a genuine choice is required.
- Prefer concise, modular changes and clear documentation updates.

