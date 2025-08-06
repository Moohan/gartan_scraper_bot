# Docker Container Deployment

## Overview

The Gartan Scraper Bot has been containerized to provide:
- **Periodic Data Collection**: Scrapes data every 5 minutes using intelligent cache rules
- **REST API Server**: Serves availability data via HTTP endpoints
- **Health Monitoring**: Built-in health checks and monitoring
- **Production Ready**: Multi-stage Docker build with non-root user

## Quick Start

### Prerequisites
- Docker and Docker Compose installed
- `.env` file with credentials:
  ```
  GARTAN_USERNAME=your_username
  GARTAN_PASSWORD=your_password
  ```

### Deployment Commands

**Production Deployment:**
```bash
# Linux/macOS
./deploy.sh

# Windows PowerShell
.\deploy.ps1
```

**Manual Deployment:**
```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

**Development Mode:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## Container Architecture

### Process Management
- **Main Process**: `container_main.py` - Orchestrates all services
- **Scheduler Process**: `scheduler.py` - Runs scraper every 5 minutes
- **API Server Process**: `api_server.py` - Serves REST API endpoints

### Data Collection Schedule
- **Every 5 minutes**: Update scrape (3 days of data)
- **Daily at 6 AM**: Comprehensive scrape (14 days of data)
- **On startup**: Initial data check and scrape if needed
- **Cache intelligence**: Uses existing cache rules (15min today, 1hr tomorrow, etc.)

### API Endpoints

**Health and Status:**
- `GET /health` - Container health check

**Crew Information:**
- `GET /v1/crew` - List all crew members
- `GET /v1/crew/{id}/available` - Is crew available now?
- `GET /v1/crew/{id}/duration` - How long is crew available?

**Appliance Information:**
- `GET /v1/appliances/{name}/available` - Is appliance available now?
- `GET /v1/appliances/{name}/duration` - How long is appliance available?

## Configuration

### Environment Variables
- `GARTAN_USERNAME` - Gartan system username
- `GARTAN_PASSWORD` - Gartan system password  
- `PORT` - API server port (default: 5000)
- `FLASK_ENV` - Flask environment (production/development)
- `FLASK_DEBUG` - Enable Flask debug mode (true/false)

### Volume Mounts
- `./gartan_availability.db` - SQLite database (persisted)
- `./crew_details.local` - Crew contact details (read-only)
- `gartan_data:/app/data` - Application data
- `gartan_cache:/app/_cache` - HTML cache files
- `gartan_logs:/app/logs` - Application logs

## Monitoring and Health Checks

### Health Check Endpoint
```bash
curl http://localhost:5000/health
```

Response when healthy:
```json
{
  "status": "healthy",
  "database": "connected", 
  "timestamp": "2025-08-06T12:34:56Z"
}
```

### Docker Health Check
The container includes built-in health checks:
- **Interval**: Every 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3 failed checks before unhealthy
- **Start Period**: 60 seconds grace period

### Logs and Monitoring
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f gartan-scraper

# Check container health
docker-compose ps
```

## Architecture Benefits

### Single Container Approach
- **Simplicity**: One container to deploy and manage
- **Resource Efficiency**: Shared Python runtime and dependencies
- **Coordinated Startup**: API waits for initial data before serving requests

### Process Isolation
- **Fault Tolerance**: If one process fails, the container restarts
- **Clean Separation**: Scheduler and API run in separate processes
- **Graceful Shutdown**: Proper signal handling for clean stops

### Data Persistence
- **SQLite Database**: Mounted to host for persistence
- **Cache Optimization**: Filesystem cache reduces external API calls
- **Log Rotation**: Automatic log file rotation and cleanup

## Troubleshooting

### Common Issues

**Container Won't Start:**
```bash
# Check logs
docker-compose logs gartan-scraper

# Check environment variables
docker-compose config
```

**API Returning Errors:**
```bash
# Check database exists and has data
curl http://localhost:5000/health

# View scheduler logs
docker-compose logs gartan-scraper | grep scheduler
```

**No Data Being Collected:**
```bash
# Check scheduler is running
docker-compose logs gartan-scraper | grep "scheduled_scrape"

# Check credentials
docker-compose exec gartan-scraper env | grep GARTAN
```

### Development Mode

For development with hot-reload:
```bash
# Start in development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Source code changes will be reflected immediately
```

## Production Considerations

### Security
- Runs as non-root user (`gartan`)
- Environment variables for sensitive data
- Read-only mounts where appropriate

### Performance  
- Multi-stage Docker build for smaller image
- Intelligent caching reduces API calls
- SQLite for low-overhead data storage

### Monitoring
- Health check endpoint for load balancer integration
- Structured logging for log aggregation
- Container restart policy for fault tolerance

## API Validation

The container includes comprehensive API validation:
```bash
# Test all endpoints
docker-compose exec gartan-scraper python validate_api.py
```

This validates that all API responses match the specification exactly.

## Next Steps

After successful deployment:
1. **Monitor Health**: Check `/health` endpoint regularly
2. **Verify Data**: Confirm data collection via logs and API responses  
3. **Production Deploy**: Use with reverse proxy (nginx) and monitoring
4. **Scale**: Consider multiple instances with load balancer if needed
