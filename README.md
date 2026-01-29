# Gartan Scraper Bot

Scrapes Gartan Availability system and provides REST API for crew and appliance availability.

## Pi Deployment

**1. Set up credentials:**

```bash
echo "GARTAN_USERNAME=your_username" > .env
echo "GARTAN_PASSWORD=your_password" >> .env
```

**2. Deploy container:**

```bash
docker-compose up -d
```

**3. Test API:**

```bash
curl http://localhost:5000/health
```

## API Endpoints

### Running the API Server

**Production:**

Use a production-grade WSGI server like `gunicorn`:

```bash
gunicorn --bind 0.0.0.0:5000 api_server:app
```

**Development:**

For local development, use the Flask development server. You **must** set the `FLASK_ENV` environment variable to `development`.

```bash
export FLASK_ENV=development
python api_server.py
```

**Crew:**

```bash
# List all crew (with display names)
curl http://localhost:5000/v1/crew

# Check availability
curl http://localhost:5000/v1/crew/1/available

# Get duration remaining
curl http://localhost:5000/v1/crew/1/duration

# Weekly hours
curl http://localhost:5000/v1/crew/1/hours-this-week
curl http://localhost:5000/v1/crew/1/hours-planned-week
```

**Appliances:**

```bash
# Check appliance availability
curl http://localhost:5000/v1/appliances/P22P6/available
curl http://localhost:5000/v1/appliances/P22P6/duration
```

## Management

**Check status:**

```bash
docker-compose ps
docker-compose logs -f
```

**Update:**

```bash
docker-compose pull && docker-compose up -d
```

## Project Structure
- `docs/`: Documentation and validation plans.
- `logs/`: Application and debug logs.
- `scripts/`: Utility scripts for deployment and verification.
- `tests/`: Unit and integration tests.

## Local Development

**Fresh start (clear database and rescrape):**

```bash
python run_bot.py --fresh-start --max-days 7
```

**Cache options:**

```bash
python run_bot.py --no-cache --max-days 3      # Force fresh data
python run_bot.py --cache-first --max-days 3   # Use cache when available
python run_bot.py --cache-only --max-days 3    # Cache only, no fetching
```
