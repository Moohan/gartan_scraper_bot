# Quick Docker Deployment

## Using Published Image (Recommended)

1. **Create environment file:**
   ```bash
   echo "GARTAN_USERNAME=your_username" > .env
   echo "GARTAN_PASSWORD=your_password" >> .env
   ```

2. **Deploy with docker-compose:**
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment:**
   ```bash
   curl http://localhost:5000/health
   ```

The service will be available at:
- **API Server**: http://localhost:5000
- **Container Name**: `gartan-scrape`
- **Image**: `${DOCKER_USERNAME}/gartan_scraper_bot:latest` (e.g. `jamesmcmahon0/gartan_scraper_bot:latest`)

## Docker Compose Configuration

Your docker-compose.yml now uses the published image:

```yaml
services:
  gartan-scraper:
    container_name: gartan-scrape
  image: ${DOCKER_IMAGE:-jamesmcmahon0/gartan_scraper_bot:latest}
    ports:
      - "5000:5000"
    environment:
      - GARTAN_USERNAME=${GARTAN_USERNAME}
      - GARTAN_PASSWORD=${GARTAN_PASSWORD}
    volumes:
      - gartan_data:/app/data
      - gartan_cache:/app/_cache
    restart: unless-stopped
```

## Automated Publishing

The Docker image is automatically published to Docker Hub via GitHub Actions:
- **Push to main**: Publishes `${DOCKER_USERNAME}/gartan_scraper_bot:latest`
- **Version tags**: Publishes `${DOCKER_USERNAME}/gartan_scraper_bot:v1.x.x`
- **Commits**: Publishes `${DOCKER_USERNAME}/gartan_scraper_bot:sha-abcd123`

No manual building required!
