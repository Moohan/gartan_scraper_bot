# PowerShell deployment script for Gartan Scraper Bot
# Usage: .\deploy.ps1

param(
    [switch]$Development = $false
)

Write-Host "🚀 Gartan Scraper Bot Deployment" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "Error: .env file not found!" -ForegroundColor Red
    Write-Host "Please create a .env file with:"
    Write-Host "GARTAN_USERNAME=your_username"
    Write-Host "GARTAN_PASSWORD=your_password"
    exit 1
}

# Check if crew_details.local exists
if (-not (Test-Path "crew_details.local")) {
    Write-Host "Warning: crew_details.local not found" -ForegroundColor Yellow
    Write-Host "Creating empty crew_details.local file..."
    New-Item -Path "crew_details.local" -ItemType File
}

# Build and start the container
Write-Host "Building Docker image..." -ForegroundColor Green

if ($Development) {
    Write-Host "Starting in development mode..." -ForegroundColor Yellow
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml build
    docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
} else {
    docker-compose build
    docker-compose up -d
}

# Wait for health check
Write-Host "Waiting for service to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Check health
Write-Host "Checking service health..." -ForegroundColor Green
$healthy = $false

for ($i = 1; $i -le 10; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Service is healthy!" -ForegroundColor Green
            $healthy = $true
            break
        }
    } catch {
        Write-Host "Waiting for service... ($i/10)"
        Start-Sleep -Seconds 10
    }
}

if (-not $healthy) {
    Write-Host "⚠️  Service may not be fully ready" -ForegroundColor Yellow
}

# Show status
Write-Host ""
Write-Host "🔍 Service Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "📊 API Endpoints:" -ForegroundColor Cyan
Write-Host "Health Check: http://localhost:5000/health"
Write-Host "Crew List:    http://localhost:5000/v1/crew"
Write-Host "API Docs:     See specification/api_specification.md"

Write-Host ""
Write-Host "📋 Management Commands:" -ForegroundColor Cyan
Write-Host "View logs:    docker-compose logs -f"
Write-Host "Stop:         docker-compose down"
Write-Host "Restart:      docker-compose restart"
Write-Host "Update:       docker-compose pull && docker-compose up -d"

Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
