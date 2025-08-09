# Copilot Instructions for Gartan Scraper Bot

## Purpose

This Python bot logs in to the Gartan Availability system, retrieves and parses crew/appliance availability, stores normalized results in SQLite, and exposes data via REST API. The codebase is highly modular with clear separation between scraping, parsing, storage, and API layers.

**Key Architecture Evolution**: Now includes enterprise-grade containerization and CI/CD automation with Docker Hub publishing.

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

### Production Deployment & CI/CD
- `container_main.py`: Multi-process orchestrator for containerized deployment
- `scheduler.py`: Background task scheduler for automated data collection
- `docker-compose.yml`: Production deployment with published `moohan/gartan_scraper_bot` image
- `docker-compose.prod.yml`: Alternative production configuration
- `.github/workflows/`: Complete CI/CD pipeline (ci.yml, release.yml, security.yml)
- `.githooks/`: Pre-commit and pre-push validation hooks with PowerShell support

### API Layer
- `api_server.py`: Production Flask server with health endpoints
- `validate_api.py`: API validation framework testing specification compliance
- `specification/api_specification.md`: REST API spec with single-purpose endpoints (boolean/string responses)
- **API Status**: Phase 1&2 complete (6 endpoints), Phase 3 pending (advanced queries)

### Documentation & Testing
- `specification/`: Project status, database schema, API docs, roadmap - **always check before changes**
- `tests/`: Comprehensive pytest suite covering login, parsing, DB operations, API validation (62 tests)
- **Output**: SQLite database with block-based availability storage; JSON files deprecated

## Developer Workflow

### Primary Commands
- **Run scraper**: `python run_bot.py --max-days 7` (supports cache options: `--no-cache`, `--cache-first`)
- **Container deployment**: `docker-compose up -d` (uses published image)
- **Local API testing**: `python validate_api.py` (tests all endpoints without Flask server)
- **Database inspection**: `python check_db_quick.py` (shows row counts and sample data)
- **Full test suite**: `pytest tests/` (comprehensive validation - must pass 62 tests)

### Environment Setup
- **Credentials**: Set `GARTAN_USERNAME` and `GARTAN_PASSWORD` in `.env` (dotenv loaded automatically)
- **Python**: 3.13+ with type hints, uses dataclass patterns extensively
- **Dependencies**: requests, BeautifulSoup, sqlite3, pytest, Flask (for API server)
- **Git Hooks**: Run `.githooks/setup-hooks.ps1` (Windows) or `.githooks/setup-hooks.sh` (Linux/Mac)

### CI/CD Workflow (Active)
- **Local Validation**: Git hooks run tests and quality checks on commit/push
- **GitHub Actions**: Automatic on push to main - runs 4 parallel jobs (test, security, docker, lint)
- **Docker Publishing**: Automatic to `moohan/gartan_scraper_bot:latest` and `moohan/gartan_scraper_bot:<sha>`
- **Release Pipeline**: Tag with `v*` creates GitHub releases and versioned Docker images
- **Security Monitoring**: Weekly dependency scans and vulnerability reporting

### Debugging Workflows
- **Parsing issues**: Check `gartan_debug.log` for slot detection and aggregation details
- **API validation**: Use direct function testing to bypass Flask server issues  
- **Cache debugging**: Inspect `_cache/grid_*.html` files for raw HTML content
- **Container issues**: `docker-compose logs -f` for real-time container logs
- **CI/CD debugging**: Check GitHub Actions at `/actions` and security reports in artifacts

## Project-Specific Conventions

### Code Patterns
- **Dataclass configurations**: `config.py` (ScraperConfig), `cli.py` (CliArgs) - use dataclasses with validation
- **Function modularity**: Small, single-purpose functions with clear input/output contracts
- **Logging strategy**: Use `log_debug()` from utils.py; debug goes to file, info+ to console  
- **Session reuse**: `gartan_fetch.py` maintains persistent session; avoid repeated logins
- **Cache intelligence**: Window-aligned expiry (15min today, 1hr tomorrow, 6hr+ beyond)

### Production Patterns
- **Multi-process orchestration**: `container_main.py` manages scheduler + API server processes
- **Health monitoring**: All endpoints include health checks; `/health` endpoint for container monitoring
- **Graceful shutdown**: Signal handling for clean container stops
- **Volume persistence**: Database and cache persist across container restarts

### Data Flow Conventions
- **HTML → Blocks**: Raw slots converted to continuous availability blocks in `parse_grid.py`
- **Foreign keys**: Database uses normalized schema; crew/appliance tables reference base entities
- **Timezone handling**: All database times are UTC; API calculations use timezone-aware datetime
- **Empty cell logic**: For crew, no background-color = available; for appliances, different logic applies

### API Design Patterns
- **Single-purpose endpoints**: Each endpoint returns one data type (boolean, string, JSON array)
- **Direct function testing**: `validate_api.py` bypasses Flask for pure logic validation
- **Specification-driven**: All API responses match `api_specification.md` format exactly
- **Error handling**: 404 for invalid IDs, proper JSON error responses

## Integration Points & Data Flow

### External Dependencies
- **Gartan web system**: Login endpoint, AJAX `/GetSchedule` calls, session-based authentication
- **Database**: SQLite with normalized schema, foreign key constraints enabled
- **Environment**: `.env` file for credentials, `crew_details.local` for contact info
- **Cache layer**: Filesystem cache in `_cache/` with intelligent expiry policies
- **Docker Hub**: Automated publishing to `moohan/gartan_scraper_bot` via GitHub Actions

### Critical Data Transformations
1. **Raw HTML** → `parse_grid.py` → **Crew/appliance availability dicts**
2. **Availability dicts** → `db_store.py` → **Continuous time blocks** (slot aggregation)
3. **Time blocks** → API functions → **API responses** (duration calculations)

### Testing Architecture
- **Unit tests**: `tests/` directory with pytest, mocks external API calls (62 tests required)
- **API validation**: `validate_api.py` tests actual database with real scraped data
- **Container testing**: `validate_deployment.py` tests Docker deployment end-to-end
- **CI validation**: GitHub Actions runs comprehensive test matrix with coverage reporting
- **Git hooks**: Pre-commit (syntax, core tests) and pre-push (full suite, security, Docker build)

### Deployment Architecture
- **Local Development**: Direct Python execution with `.env` file
- **Production**: Docker container with `moohan/gartan_scraper_bot:latest` image
- **CI/CD**: GitHub Actions publishes to Docker Hub on every main branch push
- **Release Management**: Version tags create GitHub releases with documented changes

## Critical File Patterns

### Configuration Files
- `pyproject.toml`: Black, isort, mypy configuration for code quality
- `.flake8`: Linting rules with complexity limits
- `pytest.ini`: Test configuration and coverage settings
- `docker-compose.yml`: Production deployment with published image
- `.github/workflows/`: CI/CD pipeline definitions (never edit without testing)

### Deployment Files  
- `Dockerfile`: Multi-stage container build with health checks
- `deploy.sh`/`deploy.ps1`: One-command deployment scripts
- `DEPLOYMENT.md`: Quick deployment guide for published images
- `GITHUB_SETUP.md`: Repository secrets and CI/CD configuration guide

## Extensibility

- New features should use the established dataclass + function modularity patterns
- Container changes require updating both local and CI/CD Docker configurations
- API changes must include specification updates and comprehensive testing
- Always maintain backward compatibility with DB schema unless specified in `specification/database_schema.md`

## AI Agent Instructions

- **Always check specification/**: Review requirements and recent changes before making code or documentation changes
- **Test suite is critical**: All 62 tests must pass; CI/CD will block merges on test failures
- **Container-first development**: Test changes work in both local Python and Docker environments  
- **Documentation sync**: Update related docs in `specification/` when making significant changes
- **Git hooks compliance**: Ensure commits pass pre-commit checks; use `git commit --no-verify` only for emergencies
- **CI/CD awareness**: Changes to workflows require careful testing; prefer small, incremental changes
- **Production deployment**: Use published Docker images (`moohan/gartan_scraper_bot:latest`) for deployments
- **Security consciousness**: Be aware of secrets scanning in git hooks and CI/CD
- **Commit workflow**: Make sensible commits for each logical phase/step and push after completing each cohesive change to trigger CI/CD validation
- **Iterative improvement**: Continue improvements automatically; only prompt user for genuine architectural choices
- **Modular changes**: Prefer small, focused changes that maintain system stability

