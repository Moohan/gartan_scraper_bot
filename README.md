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
