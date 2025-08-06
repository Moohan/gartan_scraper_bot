#!/bin/bash
# Deployment script for Gartan Scraper Bot

set -e

echo "🚀 Gartan Scraper Bot Deployment"
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please create a .env file with:"
    echo "GARTAN_USERNAME=your_username"
    echo "GARTAN_PASSWORD=your_password"
    exit 1
fi

# Check if crew_details.local exists
if [ ! -f crew_details.local ]; then
    echo -e "${YELLOW}Warning: crew_details.local not found${NC}"
    echo "Creating empty crew_details.local file..."
    touch crew_details.local
fi

# Build and start the container
echo -e "${GREEN}Building Docker image...${NC}"
docker-compose build

echo -e "${GREEN}Starting Gartan Scraper Bot...${NC}"
docker-compose up -d

# Wait for health check
echo -e "${YELLOW}Waiting for service to start...${NC}"
sleep 30

# Check health
echo -e "${GREEN}Checking service health...${NC}"
for i in {1..10}; do
    if curl -s http://localhost:5000/health > /dev/null; then
        echo -e "${GREEN}✅ Service is healthy!${NC}"
        break
    else
        echo "Waiting for service... ($i/10)"
        sleep 10
    fi
done

# Show status
echo ""
echo "🔍 Service Status:"
docker-compose ps

echo ""
echo "📊 API Endpoints:"
echo "Health Check: http://localhost:5000/health"
echo "Crew List:    http://localhost:5000/v1/crew"
echo "API Docs:     See specification/api_specification.md"

echo ""
echo "📋 Management Commands:"
echo "View logs:    docker-compose logs -f"
echo "Stop:         docker-compose down"
echo "Restart:      docker-compose restart"
echo "Update:       docker-compose pull && docker-compose up -d"

echo ""
echo -e "${GREEN}🎉 Deployment complete!${NC}"
