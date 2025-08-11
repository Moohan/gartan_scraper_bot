# Gartan Scraper Bot

A streamlined Python bot that logs in to the Gartan Availability system, retrieves crew and appliance availability, stores data in SQLite, and provides REST API access.

## Core Components

- **📊 Data Collection**: Automated scraping with cache optimization (`run_bot.py`)
- **🏗️ Data Processing**: HTML parsing and normalization (`parse_grid.py`)
- **💾 Data Storage**: SQLite database with availability blocks (`db_store.py`)
- **🌐 API Server**: REST endpoints for availability queries (`api_server.py`)
- **🐳 Containerization**: Docker deployment configuration
- **🧪 Testing**: Comprehensive test suite (62 tests)

## Features

- **🔐 Secure Authentication**: Environment variable credentials
- **📊 Intelligent Data Collection**: Scrapes every 5 minutes with smart caching
- **🏗️ Normalized Database**: SQLite with block-based availability storage
- **🌐 REST API**: 6 endpoints with health monitoring
- **🐳 Docker Ready**: Single container with automated deployment
- **📈 Production Monitoring**: Health checks, logging, and graceful shutdown

## Quick Start (Docker)

### Prerequisites
- Docker and Docker Compose
- Gartan system credentials

## Quick Start (Docker)

### Prerequisites
- Docker and Docker Compose
- Gartan system credentials

### Deployment

**Option 1: Use Published Image (Recommended)**
```bash
# 1. Set up credentials
echo "GARTAN_USERNAME=your_username" > .env
echo "GARTAN_PASSWORD=your_password" >> .env

# 2. Deploy with published image
docker-compose up -d

# 3. Verify deployment
curl http://localhost:5000/health
```

**Option 2: Local Build**
```bash
# 1. Set up credentials
echo "GARTAN_USERNAME=your_username" > .env
echo "GARTAN_PASSWORD=your_password" >> .env

# 2. Deploy with automated scripts
# Linux/macOS
./deploy.sh

# Windows PowerShell
.\deploy.ps1

# 3. Verify deployment
python validate_deployment.py
```

### API Usage

Once deployed, the API is available at `http://localhost:5000`:

```bash
# Check service health
curl http://localhost:5000/health

# Get crew list
curl http://localhost:5000/v1/crew

# Check if crew member 1 is available
curl http://localhost:5000/v1/crew/1/available

# Get availability duration (returns string hours like "2.5h" or null)
curl http://localhost:5000/v1/crew/1/duration

# Weekly hours (actual since Monday / planned for full week)
curl http://localhost:5000/v1/crew/1/hours-this-week
curl http://localhost:5000/v1/crew/1/hours-planned-week

# Check appliance availability
curl http://localhost:5000/v1/appliances/P22P6/available
```

## Recent Updates

### v1.2.1 - Duration Format & Weekly Hours (2025-08-11)

- **⏱ Duration Format**: `/duration` endpoints now return an hours string (e.g. `"3.25h"`) or `null` (was previously minutes JSON). Keeps API concise & spec-aligned.
- **📅 Weekly Hours Endpoints**: Added `/hours-this-week` and `/hours-planned-week` for per‑crew aggregation.
- **🗄 Persistent DB Init**: Database initialization is now non‑destructive by default; set `RESET_DB=1` env var to force a rebuild.
- **🧪 Tests**: 77 tests passing; legacy demo test scripts moved under `examples/` or deprecated.

### v1.2.0 - Codebase Cleanup (2025-08-08)

- **🧹 Major Cleanup**: Reduced codebase by 40% (removed ~20 non-essential files)
- **🔧 Core Focus**: Streamlined to 6 essential components (read, process, store, serve, containerize, test)
- **✅ Validation**: All 62 core tests passing, real data integration confirmed
- **🚀 API Fixes**: All 6 REST endpoints working correctly
- **📦 Minimal Config**: Lightweight configuration management with environment variable support

**Files Removed**: test_compatibility.py, test_direct_api.py, validate_*.py, check_db.py, improvements/ directory
**Files Created**: Minimal config.py, connection_manager.py, cli.py replacements

## Architecture

### Container Components
- **Scheduler Process**: Collects data every 5 minutes
- **API Server Process**: Serves REST endpoints
- **Orchestrator**: Manages both processes with health monitoring
- **SQLite Database**: Persisted availability data

### Data Collection Schedule

- **Every 5 minutes**: Update scrape (3 days of data)
- **Daily at 6 AM**: Comprehensive scrape (14 days of data)
- **Startup**: Initial data check and scrape if needed

## Development

### Local Development

Run without Docker for development:

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run scraper once
python run_bot.py --max-days 7

# Test API functions
python validate_api.py

# Start API server
python api_server.py
```

### Docker Development Mode

```bash
# Start in development mode with hot-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Architecture Overview

### Core Components (Summary)

- `run_bot.py`: Main scraper orchestrator
- `api_server.py`: Production Flask API server
- `scheduler.py`: Background task scheduler
- `container_main.py`: Multi-process orchestrator
- `gartan_fetch.py`: Session management and data fetching
- `parse_grid.py`: HTML parsing and availability detection
- `db_store.py`: Database schema and storage

### Data Flow

1. **Scheduler** triggers scraper every 5 minutes
2. **Scraper** logs in and fetches HTML grids
3. **Parser** extracts crew/appliance availability
4. **Database** stores availability as time blocks
5. **API** serves real-time availability queries

## API Specification

### Endpoints

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| `/health` | GET | JSON | Service health status |
| `/v1/crew` | GET | JSON Array | All crew members |
| `/v1/crew/{id}/available` | GET | Boolean | Is crew available now? |
| `/v1/crew/{id}/duration` | GET | String/null | Availability duration |
| `/v1/appliances/{name}/available` | GET | Boolean | Is appliance available? |
| `/v1/appliances/{name}/duration` | GET | String/null | Availability duration |

**Phase 3 Endpoints** (Coming Soon):

- Next availability change times
- Duration of next availability periods
- Current crew operating appliances

See `specification/api_specification.md` for complete details.

## Configuration

### Environment Variables

- `GARTAN_USERNAME`: Gartan system username (required)
- `GARTAN_PASSWORD`: Gartan system password (required)
- `PORT`: API server port (default: 5000)
- `FLASK_ENV`: Flask environment (production/development)

### Files

- `.env`: Environment variables
- `crew_details.local`: Crew contact information
- `gartan_availability.db`: SQLite database (auto-created)

## Monitoring and Operations

### Health Monitoring

```bash
# Check container status
docker-compose ps

# View real-time logs
docker-compose logs -f

# Check API health
curl http://localhost:5000/health
```

### Management Commands

```bash
# Stop services
docker-compose down

# Restart services
docker-compose restart

# Update and redeploy
docker-compose pull && docker-compose up -d

# View database
python check_db.py
```

## Testing

### Validation Scripts

- `validate_api.py`: Test API functions directly
- `validate_deployment.py`: Test Docker deployment
- `test_container.py`: Test container components
- `pytest tests/`: Full test suite

### Data Validation

```bash
# Check database contents
python check_db.py

# Verify API compliance
python validate_api.py
```

## Documentation

- `DOCKER_README.md`: Complete Docker deployment guide
- `CONTAINER_SUMMARY.md`: Containerization implementation summary
- `specification/`: Database schema, API spec, project status
- `.github/copilot-instructions.md`: AI agent development guide

## Production Deployment

For production deployment:

1. **Server Setup**: Install Docker and Docker Compose
2. **Reverse Proxy**: Configure nginx for SSL termination
3. **Monitoring**: Set up log aggregation and health alerts
4. **Backup**: Schedule database backups
5. **Updates**: Use blue-green deployment with health checks

See `DOCKER_README.md` for detailed production configuration.

## Contributing

1. Check `specification/project_status.md` for current priorities
2. Review `.github/copilot-instructions.md` for development patterns
3. Run tests before submitting changes: `pytest tests/`
4. Update documentation for new features

## License

Internal fire service use.

## 🎯 CI/CD Pipeline Status: ACTIVE ✅

Automated Docker Hub publishing is now live! Every push to main automatically:

- Runs comprehensive test suite (62 tests)
- Builds and publishes to moohan/gartan_scraper_bot
- Creates versioned releases and security scans

Deploy anywhere with: `docker-compose up -d`
