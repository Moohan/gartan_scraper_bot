# Pi Deployment Guide

## Quick Setup

**1. Create .env file:**

```bash
echo "GARTAN_USERNAME=your_username" > .env
echo "GARTAN_PASSWORD=your_password" >> .env
```

**2. Deploy:**

```bash
docker-compose up -d
```

**3. Test:**

```bash
curl http://localhost:5000/health
curl http://localhost:5000/v1/crew
```

## Container Details

- **Image**: `jamesmcmahon0/gartan_scraper_bot:latest` (auto-built)
- **Port**: 5000
- **Data**: Persisted in Docker volumes
- **Restart**: Automatic unless stopped

## Management

```bash
# Check status
docker-compose ps
docker-compose logs -f

# Update
docker-compose pull && docker-compose up -d

# Stop
docker-compose down
```
