# Gartan Scraper Bot

Scrapes Gartan Availability system and provides REST API for crew and appliance availability.

## Pi Deployment

**1. Set up credentials:**

Create a `.env` file for your local environment variables. You can use the provided example file as a template:

```bash
cp .env.example .env
```

Next, open the `.env` file and replace the placeholder values with your actual Gartan username and password.

**IMPORTANT:** The `.env` file is included in `.gitignore` and should never be committed to the repository to avoid exposing sensitive credentials.

**2. Deploy container:**

```bash
docker-compose up -d
```

**3. Test API:**

```bash
curl http://localhost:5000/health
```

## API Endpoints

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
