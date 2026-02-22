# Deployment Guide

This guide is intended for users deploying the Gartan Scraper Bot as a Docker container to an always-on machine, such as a Raspberry Pi. The deployed container runs a background scheduler that periodically fetches new data to be served via the REST API.

## Requirements

- **Docker** and **Docker Compose** installed.
- Valid Gartan credentials.

## 1. Quick Setup (Raspberry Pi & General Linux)

The project includes an automated deployment script for Raspberry Pi that manages permissions, folders, and Docker Compose configurations.

```bash
# Clone the repository
git clone https://github.com/your-repo/gartan_scraper_bot.git
cd gartan_scraper_bot

# Copy the example environment variable file
cp .env.example .env

# Edit the environment file to set your credentials and configuration
nano .env
```

### Important Environment Settings (`.env`)

```ini
GARTAN_USERNAME=your_username
GARTAN_PASSWORD=your_password
PORT=5000

# Fix Permissions on Raspberry Pi (Optional but recommended)
# Set your user ID and group ID to avoid root-owned volume files
USER_ID=1000
GROUP_ID=1000

# Specify custom directories to store persisted data if needed
DATA_PATH=/media/elements/gartan/data
CACHE_PATH=/media/elements/gartan/cache
LOGS_PATH=/media/elements/gartan/logs
```

## 2. Deploy the Container

The project relies on a unified `docker-compose.yml` that handles both development and production (by overriding variables).

Start the service in detached mode:

```bash
docker-compose up -d
```

### What happens next?

1. The container starts up and runs `container_main.py`.
2. A background **scheduler** begins executing `Gartran_fetch` operations asynchronously every few minutes.
3. The **Flask API** spins up and listens on port 5000 (`http://localhost:5000`).

## 3. Verify Deployment & Health

Check the API endpoint to ensure the core services are healthy.

```bash
curl http://localhost:5000/health
```

*(Should return `{"status": "healthy", "database": "connected"}`)*

Check that the crew data is being served correctly:

```bash
curl http://localhost:5000/v1/crew
```

## 4. Container Management

### Viewing Logs

The easiest way to debug issues or see the scheduler in action is to review the logs:

```bash
docker-compose logs -f
```

### Updating to the Latest Release

If the codebase on GitHub changes and a new tagged release or commit to `main` completes the CI workflow, the Docker image on Docker Hub will be updated automatically.

To pull those changes and seamlessly restart your container use:

```bash
docker-compose pull && docker-compose up -d
```

### Stopping the Service

```bash
docker-compose down
```

## Migration Note

If you are migrating from an older configuration (with `deploy/pi-docker-compose.yml` or `docker-compose.prod.yml`), those files have been removed. The unified `docker-compose.yml` now relies on `.env` overrides to handle custom paths and production-ready images. Simply set `DOCKER_IMAGE=jamesmcmahon0/gartan_scraper_bot:latest` and run `docker-compose up -d`.
