# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.1] - 2025-08-11

### Added
- **📅 Weekly Hours Endpoints**: Added `/hours-this-week` and `/hours-planned-week` for per‑crew aggregation
- **🗄 Persistent DB Init**: Database initialization is now non‑destructive by default; set `RESET_DB=1` env var to force a rebuild

### Changed
- **⏱ Duration Format**: `/duration` endpoints now return an hours string (e.g. `"3.25h"`) or `null` (was previously minutes JSON). Keeps API concise & spec-aligned

### Testing
- **🧪 Tests**: 77 tests passing; legacy demo test scripts moved under `examples/` or deprecated

## [1.2.0] - 2025-08-08

### Added
- **🔧 Core Focus**: Streamlined to 6 essential components (read, process, store, serve, containerize, test)
- **📦 Minimal Config**: Lightweight configuration management with environment variable support

### Changed
- **🧹 Major Cleanup**: Reduced codebase by 40% (removed ~20 non-essential files)

### Fixed
- **🚀 API Fixes**: All 6 REST endpoints working correctly

### Removed
**Files Removed**: test_compatibility.py, test_direct_api.py, validate_*.py, check_db.py, improvements/ directory

**Files Created**: Minimal config.py, connection_manager.py, cli.py replacements

### Testing
- **✅ Validation**: All 62 core tests passing, real data integration confirmed

## CI/CD Pipeline Activation

### 🎯 CI/CD Pipeline Status: ACTIVE ✅

Automated Docker Hub publishing is now live! Every push to main automatically:

- Runs comprehensive test suite (62 tests)
- Builds and publishes to ${DOCKER_USERNAME}/gartan_scraper_bot (configured via secrets, default jamesmcmahon0)
- Creates versioned releases and security scans

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