# Changelog

## [Unreleased] - 2025-08-26

### Fixed

- **🐛 Critical Database Issue**: Fixed stale data corruption where unavailable crew appeared available
- **⚠️ W Status Parsing**: Correctly parses unavailable (W) status from Gartan system
- **🔄 Database Cleanup**: Added automatic cleanup of overlapping availability blocks during data insertion
- **⚙️ CLI Arguments**: Fixed cache mode inconsistencies (`--no-cache` vs `--cache-off`)

### Added

- **✅ Ground Truth Validation**: Manual validation process against real-world availability data
- **🎯 Enhanced CLI**: Added `--cache-first` option for explicit cache preference
- **🔍 Database Debugging**: Better logging and investigation tools for data quality issues
- **🔄 Fresh Start Option**: Added `--fresh-start` flag to clear database and force complete rescrape

### Changed

- **💾 Database Storage**: `insert_crew_availability()` now cleans up conflicting blocks before insertion
- **🖥️ CLI Interface**: Removed unused `--force-scrape` argument for cleaner interface
- **📖 Documentation**: Updated README with new CLI options and features

### Technical Details

- Fixed parsing where GIBB, OL and MUNRO, MA incorrectly showed as available
- All 7 crew members now correctly match ground truth availability status
- Database blocks are cleaned up by date range to prevent stale data accumulation
- Fresh scraping bypasses cache completely with `--no-cache` option

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
- **💾 Persistent DB**: Non-destructive database initialization

### Changed

- **⏱ Duration Format**: API returns hours string (e.g., `"3.25h"`) or `null`

## [1.2.0] - 2025-08-08

### Added

- **🐳 Container Deployment**: Full Docker containerization with health checks
- **🔄 Automated Scheduler**: Background data collection every 5 minutes
- **📊 Production Ready**: Multi-process orchestration for containerized deployment

### Changed

- **🏗️ Architecture**: Unified production deployment with environment variable controls
- **💾 Volume Persistence**: Database and cache persist across container restarts

## [1.1.0] - 2025-08-05

### Added

- **📊 Database Schema**: Comprehensive SQLite database with normalized schema
- **🔍 API Endpoints**: REST API with crew and appliance availability endpoints
- **⚡ Caching System**: Intelligent cache management with window-aligned expiry

### Changed

- **🔧 Modular Design**: Clear separation between scraping, parsing, storage, and API layers
- **📖 Documentation**: Complete specification and deployment guides

## [1.0.0] - 2025-08-01

### Added

- **🎯 Core Scraping**: Initial implementation of Gartan availability scraper
- **📋 HTML Parsing**: BeautifulSoup-based grid parsing with crew/appliance detection
- **🔐 Session Management**: Persistent login and AJAX call handling
- **📝 Logging**: Structured logging with file rotation and debug capabilities

### Infrastructure

- **🐍 Python 3.13+**: Modern Python with type hints and dataclass patterns
- **🧪 Test Suite**: Comprehensive pytest coverage for all components
- **🔄 CI/CD**: GitHub Actions pipeline with automated testing and deployment
