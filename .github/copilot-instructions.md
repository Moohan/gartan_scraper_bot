# Copilot Instructions for Gartan Scraper Bot

## Purpose

This Python bot logs in to the Gartan Availability system, retrieves and parses crew/appliance availability, stores normalized results in SQLite, and exposes data via REST API. The codebase is highly modular with clear separation between scraping, parsing, storage, and API layers.

**Current Status**: Production-ready with enhanced display names, deployed on Raspberry Pi 5 with automated Docker publishing.

## Architecture & Key Files

### Core Scraping Engine
- `run_bot.py`: Main orchestrator. Handles multi-threaded fetching, progress/ETA tracking, CLI args, logging setup.
- `gartan_fetch.py`: Session management, login, AJAX calls to `/GetSchedule`, intelligent caching with window-aligned expiry.
- `parse_grid.py`: HTML parsing with crew/appliance detection, slot-to-block conversion, availability aggregation.
- `db_store.py`: Normalized SQLite schema with foreign keys, block-based storage for efficient queries.

### Configuration & Infrastructure
- `config.py`: Container-aware configuration (paths differ for `/app` vs local), cache expiry rules, environment variable access.
- `cli.py`: Argument parsing and validation with dataclass patterns.
- `logging_config.py`: Structured logging with file rotation, separate debug/console levels.
- `cache_utils.py`: Cache file naming, timestamp alignment, cleanup logic.

### Production Deployment & CI/CD
- `container_main.py`: Multi-process orchestrator for containerized deployment
- `scheduler.py`: Background task scheduler for automated data collection every 5 minutes
- `docker-compose.yml`: Unified production deployment with environment variable controls
- `docker-compose.dev.yml`: Development override for hot-reload
- `.github/workflows/`: Complete CI/CD pipeline (ci.yml, release.yml, security.yml)
- **Docker Hub**: Auto-published as `jamesmcmahon0/gartan_scraper_bot:latest`

### API Layer
- `api_server.py`: Production Flask server with health endpoints and display name support
- `specification/api_specification.md`: Simplified REST API spec focusing on essential endpoints
- **API Status**: Phase 1&2 complete (6 endpoints) with display names feature

### Documentation & Testing
- `specification/`: Project status, database schema, API docs - **streamlined and Pi-focused**
- `tests/`: Comprehensive pytest suite covering all components (77 tests must pass)
- **Contact Data**: Enhanced format with emails/positions in `crew_details.local`

## Developer Workflow

### Primary Commands
- **Run scraper**: `python run_bot.py --max-days 7` (supports cache options: `--no-cache`, `--cache-first`)
- **Container deployment**: `docker-compose up -d` (uses published `jamesmcmahon0/gartan_scraper_bot:latest`)
- **Database inspection**: `python check_db_quick.py` (shows row counts and sample data)
- **Full test suite**: `pytest tests/` (comprehensive validation - must pass 77 tests)

### Environment Setup
- **Credentials**: Set `GARTAN_USERNAME` and `GARTAN_PASSWORD` in `.env` (dotenv loaded automatically)
- **Python**: 3.13+ with type hints, uses dataclass patterns extensively
- **Dependencies**: requests, BeautifulSoup, sqlite3, pytest, Flask (for API server)

### Debugging Workflows
- **Parsing issues**: Check `gartan_debug.log` for slot detection and aggregation details
- **Cache debugging**: Inspect `_cache/grid_*.html` files for raw HTML content
- **Container issues**: `docker-compose logs -f` for real-time container logs
- **API testing**: Direct curl commands or use test functions in `tests/test_*.py`

## Project-Specific Conventions

### Code Patterns
- **Container-aware config**: `config.py` detects `/app` directory to set container vs local paths
- **Enhanced contact format**: `crew_details.local` uses `SURNAME, INITIALS|Display Name|Phone|Email|Position`
- **Display name extraction**: API extracts friendly names from contact field: `contact.split("|")[0]`
- **Function modularity**: Small, single-purpose functions with clear input/output contracts
- **Session reuse**: `gartan_fetch.py` maintains persistent session; avoid repeated logins
- **Cache intelligence**: Historic data (-1 day) = infinite cache, today = 15min, future = 24hr

### Production Patterns
- **Unified Docker config**: Single `docker-compose.yml` with environment variable controls (`DATA_PATH`, `CACHE_PATH`, etc.)
- **Multi-process orchestration**: `container_main.py` manages scheduler + API server processes
- **Volume persistence**: Database and cache persist across container restarts in Docker volumes
- **Health monitoring**: `/health` endpoint for container monitoring with database connectivity checks

### Data Flow Conventions
- **HTML → Blocks**: Raw 15-minute slots converted to continuous availability blocks in `parse_grid.py`
- **Contact integration**: Enhanced contact data stored in `crew.contact` field during scraping
- **Display names**: API returns both formal name (`MCMAHON, JA`) and display name (`James McMahon`)
- **Timezone handling**: All database times are UTC; API calculations use timezone-aware datetime
- **Empty cell logic**: For crew, no background-color = available; for appliances, green (#009933) = available

### API Design Patterns
- **Single-purpose endpoints**: Each endpoint returns one data type (boolean, string, JSON array)
- **Display name support**: `/v1/crew` includes both `name` and `display_name` fields
- **Error handling**: 404 for invalid IDs, proper JSON error responses
- **Specification-driven**: All API responses match simplified `api_specification.md` format

## Integration Points & Data Flow

### External Dependencies
- **Gartan web system**: Login endpoint, AJAX `/GetSchedule` calls, session-based authentication
- **Database**: SQLite with normalized schema, foreign key constraints enabled
- **Environment**: `.env` file for credentials, `crew_details.local` for enhanced contact info
- **Docker Hub**: Automated publishing to `jamesmcmahon0/gartan_scraper_bot` via GitHub Actions
- **Production deployment**: Raspberry Pi 5 at 192.168.86.4 with persistent Docker volumes

### Critical Data Transformations
1. **Raw HTML** → `parse_grid.py` → **Crew/appliance availability dicts**
2. **Contact file** → `run_bot.py` → **Enhanced contact data** (display names, emails, positions)
3. **Availability dicts** → `db_store.py` → **Continuous time blocks** (slot aggregation)
4. **Time blocks + contact data** → API functions → **API responses with display names**

### Testing Architecture
- **Unit tests**: `tests/` directory with pytest, 77 tests covering all components
- **Container testing**: Docker build validation in CI/CD
- **API validation**: Direct function testing of API endpoints
- **Git hooks**: Pre-commit (syntax, core tests) and pre-push (full suite, security, Docker build)

## AI Agent Instructions

- **Check specification/ first**: Review `project_status.md` and `database_schema.md` before making changes
- **Test suite is critical**: All 77 tests must pass; CI/CD will block merges on test failures
- **Container-first development**: Test changes work in both local Python and Docker environments
- **Display names**: When working with crew data, ensure both formal names and display names are handled
- **Environment awareness**: Use `config.py` for all paths - it auto-detects container vs local environment
- **Documentation sync**: Keep simplified docs focused on Pi deployment and API usage
- **Production deployment**: Changes auto-deploy via CI/CD to `jamesmcmahon0/gartan_scraper_bot:latest`
- **Contact data format**: Follow 5-field format: `SURNAME, INITIALS|Display Name|Phone|Email|Position`
- **Commit workflow**: Make focused commits; CI/CD validates and publishes automatically
- **Iterative improvement**: Continue improvements automatically; only prompt for architectural decisions
- **Docker volumes**: Understand that `/app/data`, `/app/_cache`, `/app/logs` persist across container restarts

## Git Workflow & Release Management

### Commit Process (After Every Tested Change)
1. **Test Changes**: Ensure all relevant tests pass before committing
2. **Inspect Status**: Run `git status` to see what files have changed
3. **Review Changes**: Use `git diff` to review specific changes before staging
4. **Check History**: Use `git log --oneline -n 5` to understand recent commits
5. **Stage & Commit**: `git add .` then focused commit with clear message
6. **Verify Clean State**: Confirm `git status` shows clean working directory

### Push Process (For Significant Changes or Docker Updates)
1. **Pre-Push Checks**: 
   - `git status` to ensure local environment is clean
   - `git log --oneline -n 3` to verify commits are ready
2. **Update with Remote**: `git pull --rebase` to sync with remote changes
3. **Push Changes**: `git push` (triggers CI/CD pipeline and Docker rebuild)
4. **Create Release**: After successful CI/CD, create git tag and GitHub release:
   ```bash
   git tag -a v1.x.x -m "Version 1.x.x: Brief description"
   git push origin v1.x.x
   # Then create GitHub release via web interface
   ```

### When to Push & Release
- **Significant Features**: New CLI options, API endpoints, major fixes
- **Docker Updates Needed**: When remote testing on Pi is required
- **Production Deployment**: When changes need to be available on `jamesmcmahon0/gartan_scraper_bot:latest`
- **Multiple Related Changes**: Bundle logically related commits before pushing

### Release Naming Convention
- **Major**: `v2.0.0` - Breaking changes, new architecture
- **Minor**: `v1.3.0` - New features, significant enhancements  
- **Patch**: `v1.2.1` - Bug fixes, minor improvements

## Business Rules & Data Validation

### Critical Business Rules (Must Be Enforced)
1. **Appliance TTR Dependency**: P22P6 appliance can only be available if someone with the TTR skill is available
2. **Appliance LGV Dependency**: P22P6 appliance requires at least one person with the LGV skill to be available
3. **Minimum Crew Requirement**: P22P6 appliance can only be available if at least 4 total crew members are available
   3.1. **BA Skill Requirement**: The crew of 4 must have at least 2 people with the BA skill (not including the officer - TTR skill)
   3.2. **Rank Requirement**: At least one of the BA-skilled crew must be at least FFC (Firefighter Competent) rank
4. **Daily Hour Limits**: No crew member or appliance can exceed 24 hours availability in a single day
5. **Weekly Hour Limits**: No crew member or appliance can exceed 168 hours availability in a single week
6. **Data Quality Filters**: API applies duration ≤7 days and recency ≥7 days filters to exclude corrupted data

### Crew Skill & Rank Mapping
- **TTR Skill**: Required for appliance operation (Officer role - any crew member with TTR skill)
- **LGV Skill**: At least one required for appliance operation (Driver capability)
- **BA Skill**: At least 2 required (excluding TTR officer) for appliance operation (Breathing Apparatus)
- **Rank Hierarchy**: WC (Watch Commander) > CC (Crew Commander) > FFC (Firefighter Competent) > FFD (Firefighter Development) > FFT (Firefighter Trainee)
- **Minimum Rank**: At least one FFC+ required among BA-skilled crew for appliance operation

### API Protection Mechanisms
- **Overlap Merging**: `merge_time_periods()` function prevents double-counting of overlapping availability blocks
- **Quality Filters**: SQL queries filter out impossible durations and old data
- **Boundary Clamping**: Week calculations properly bounded to prevent future time inclusion
- **Business Rule Validation**: Real-time compliance checking for appliance availability dependencies

## Extensibility

- New features should use the established dataclass + function modularity patterns
- Container changes require updating both local and CI/CD Docker configurations
- API changes must include specification updates and comprehensive testing
- Always maintain backward compatibility with DB schema unless specified in `specification/database_schema.md`
- **Business rules must be preserved**: Any API changes must maintain enforcement of the 6 critical business rules

## AI Agent Instructions

- **Always check specification/**: Review requirements and recent changes before making code or documentation changes
- **Test suite is critical**: All 77 tests must pass; CI/CD will block merges on test failures
- **Container-first development**: Test changes work in both local Python and Docker environments
- **Documentation sync**: Update related docs in `specification/` when making significant changes
- **Git hooks compliance**: Ensure commits pass pre-commit checks; use `git commit --no-verify` only for emergencies
- **CI/CD awareness**: Changes to workflows require careful testing; prefer small, incremental changes
- **Production deployment**: Use published Docker images (`jamesmcmahon0/gartan_scraper_bot:latest`) for deployments
- **Security consciousness**: Be aware of secrets scanning in git hooks and CI/CD
- **Git Workflow**: Follow commit-test-push-release cycle for all changes
- **Iterative improvement**: Continue improvements automatically; only prompt user for genuine architectural choices
- **Modular changes**: Prefer small, focused changes that maintain system stability

### Git Workflow Requirements
- **After Every Tested Change**: Commit immediately with clear, focused message
- **Before Every Commit**: Run `git status`, `git diff`, and relevant tests
- **Before Every Push**: Check `git status`, `git pull --rebase`, ensure clean state
- **After Significant Pushes**: Create git tag and GitHub release for version tracking
- **Docker Updates**: Push only when remote Pi testing or production deployment needed
