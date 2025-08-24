#!/bin/bash
set -euo pipefail

# Configuration
PI_USER="james"
PI_HOST="192.168.86.4"
PI_GARTAN_DIR="/home/james/gartan" # Use absolute path
PI_DATA_DIR="/media/elements/gartan"
LOCAL_COMPOSE_FILE="./docker-compose.yml"
LOCAL_ENV_FILE="./.env.pi.example"
REMOTE_COMPOSE_FILE="${PI_GARTAN_DIR}/docker-compose.yml"
REMOTE_ENV_FILE="${PI_GARTAN_DIR}/.env"

echo "### Starting Raspberry Pi Deployment ###"

# 1. Create remote directories and set permissions
echo "--> Ensuring remote directories exist and have correct permissions..."
ssh "${PI_USER}@${PI_HOST}" "mkdir -p ${PI_GARTAN_DIR} && sudo mkdir -p ${PI_DATA_DIR}/{data,cache,logs} && sudo chown -R ${PI_USER}:${PI_USER} ${PI_DATA_DIR}"

# 2. Copy docker-compose file and sample env to Pi
echo "--> Copying docker-compose and .env files to ${PI_USER}@${PI_HOST}:${PI_GARTAN_DIR}..."
scp "${LOCAL_COMPOSE_FILE}" "${PI_USER}@${PI_HOST}:${REMOTE_COMPOSE_FILE}"
scp "${LOCAL_ENV_FILE}" "${PI_USER}@${PI_HOST}:${REMOTE_ENV_FILE}.example"

# 3. Pull latest docker image and restart services
echo "--> Logging into Pi to pull image and restart services..."
ssh "${PI_USER}@${PI_HOST}" << 'EOF'
    set -euo pipefail
    cd "/home/james/gartan"

    echo "--- Checking for .env file ---"
    if [ ! -f .env ]; then
        echo "No .env file found. Creating from example..."
        if [ -f .env.example ]; then
            cp .env.example .env
            echo "Please edit .env file with your actual credentials before running again!"
            exit 1
        else
            echo "ERROR: No .env.example file found. Please create .env manually."
            exit 1
        fi
    fi

    echo "--- Sourcing environment variables from .env file ---"
    set -a # Automatically export all variables
    source .env
    set +a

    echo "--- Pulling latest image: ${DOCKER_IMAGE:-jamesmcmahon0/gartan_scraper_bot:latest} ---"
    docker-compose pull

    echo "--- Stopping and removing old container (if exists) ---"
    docker-compose down

    echo "--- Starting new container ---"
    docker-compose up -d

    echo "--- Deployment status ---"
    docker-compose ps

    echo "--- Last 20 lines of logs ---"
    sleep 5 # Give the container a moment to start
    docker-compose logs --tail=20
EOF

echo "### Deployment to Raspberry Pi finished ###"
