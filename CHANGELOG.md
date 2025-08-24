# Changelog

## [1.3.0] - 2025-08-24

### Added
- **👥 Display Names**: Enhanced crew API with friendly display names from contact data
- **📧 Contact Info**: Full contact format with emails and positions
- **🐳 Auto-Built Images**: Docker images auto-published to `jamesmcmahon0/gartan_scraper_bot:latest`

### Changed
- **📚 Simplified Docs**: Streamlined documentation focused on Pi deployment and API usage
- **🔧 Unified Config**: Single docker-compose.yml with intelligent defaults

## [1.2.1] - 2025-08-11

### Added
- **📅 Weekly Hours**: `/hours-this-week` and `/hours-planned-week` endpoints
- **� Persistent DB**: Non-destructive database initialization

### Changed
- **⏱ Duration Format**: API returns hours string (e.g., `"3.25h"`) or `null`

## [1.2.0] - 2025-08-08

### Added
- **� Container Deployment**: Full Docker containerization with health checks
- **� REST API**: 6 core endpoints for crew and appliance availability
- **⚡ Automated Scheduling**: Data collection every 5 minutes

### Changed
- **🧹 Streamlined**: 40% code reduction, focused on core functionality

Deploy anywhere with: `docker-compose up -d`

### GitHub Actions Workflows

The CI/CD pipeline automatically:

- **On every push to main**: Build and publish `${DOCKER_USERNAME}/gartan_scraper_bot:latest`
- **On every commit**: Build and publish `${DOCKER_USERNAME}/gartan_scraper_bot:sha-abcd123`
- **On version tags**: Create releases and publish `${DOCKER_USERNAME}/gartan_scraper_bot:v1.x.x`

### Automated Publishing

The Docker image is automatically published to Docker Hub via GitHub Actions:
- **Push to main**: Publishes `${DOCKER_USERNAME}/gartan_scraper_bot:latest`
- **Version tags**: Publishes `${DOCKER_USERNAME}/gartan_scraper_bot:v1.x.x`
- **Commits**: Publishes `${DOCKER_USERNAME}/gartan_scraper_bot:sha-abcd123`

No manual building required!

## Architecture Evolution

Historical and deep-dive documents retained for reference in `docs/archive/`:

- ACTIVATION_GUIDE.md
- CI_CD_SETUP_COMPLETE.md
- PHASE1_COMPLETION.md
- PHASE2_COMPLETION.md
- PHASE3_COMPLETION.md
- INFINITE_CACHE_IMPLEMENTATION.md
- WEEKLY_API_IMPLEMENTATION.md
- WEEKLY_API_SUMMARY.md
- WEEK_ALIGNED_FETCHING.md
- IMPROVEMENT_PLAN.md

Current architecture: see `docs/architecture.md`.

## Repository Setup Checklist

- [x] Git hooks configured (pre-commit, pre-push)
- [x] GitHub Actions workflows created (ci.yml, release.yml, security.yml)
- [x] Docker Hub publishing configured
- [x] docker-compose.yml updated for published image
- [ ] GitHub secrets configured (DOCKER_USERNAME, DOCKER_PASSWORD)
- [ ] First push to trigger initial image build
