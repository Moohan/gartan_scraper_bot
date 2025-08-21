# Gartan Scraper Bot

A Python bot that logs in to the Gartan Availability system, retrieves crew and appliance availability, stores data in SQLite, and provides REST API access.

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

## API Usage

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

## API Endpoints

| Endpoint | Method | Response | Description |
|----------|--------|----------|-------------|
| `/health` | GET | JSON | Service health status |
| `/v1/crew` | GET | JSON Array | All crew members |
| `/v1/crew/{id}/available` | GET | Boolean | Is crew available now? |
| `/v1/crew/{id}/duration` | GET | String/null | Availability duration |
| `/v1/crew/{id}/hours-this-week` | GET | String | Hours since Monday |
| `/v1/crew/{id}/hours-planned-week` | GET | String | Total planned weekly hours |
| `/v1/appliances/{name}/available` | GET | Boolean | Is appliance available? |
| `/v1/appliances/{name}/duration` | GET | String/null | Availability duration |

## Configuration

### Environment Variables

- `GARTAN_USERNAME`: Gartan system username (required)
- `GARTAN_PASSWORD`: Gartan system password (required)
- `PORT`: API server port (default: 5000)
- `RESET_DB`: Set to `1` to force database rebuild

### Files

- `.env`: Environment variables
- `crew_details.local`: Crew contact information (optional)
- `gartan_availability.db`: SQLite database (auto-created)

## Operations

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
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your credentials

# Run scraper once
python run_bot.py --max-days 7

# Start API server
python api_server.py

# Run tests
pytest tests/
```

## Documentation

- [`CHANGELOG.md`](CHANGELOG.md): Version history and changes
- [`DEPLOYMENT.md`](DEPLOYMENT.md): Quick Docker deployment guide
- [`docs/architecture.md`](docs/architecture.md): Technical architecture details
- [`.github/copilot-instructions.md`](.github/copilot-instructions.md): Development guide

## Production Deployment

For production deployment:

1. **Server Setup**: Install Docker and Docker Compose
2. **Environment**: Set `GARTAN_USERNAME` and `GARTAN_PASSWORD` in `.env`
3. **Deploy**: Run `docker-compose up -d`
4. **Monitor**: Check `/health` endpoint and container logs
5. **Updates**: Use `docker-compose pull && docker-compose up -d`

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for detailed configuration.

## License

Internal fire service use.
