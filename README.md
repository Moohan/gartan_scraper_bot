# Gartan Scraper Bot

Scrapes the Gartan Availability system and provides a REST API for crew and appliance availability. This tool allows for both real-time queries and historical scheduling analysis by calculating availability durations.

## Documentation

The project documentation has been organized into three sections to best address the needs of LLMs, local developers, and system administrators.

1. **[LLM Context & Developer Guide](docs/LLM_CONTEXT.md)**
    * **Audience:** Large Language Models (LLMs) assisting with development, and human contributors.
    * **Content:** Project aims, core architecture overview, database structures, business rules (TTR and appliance minimum staffing), and instructions on how to run tests.

2. **[Local Usage Guide](docs/LOCAL_USAGE.md)**
    * **Audience:** Users configuring and running the scraper on their local machine.
    * **Content:** Installation requirements, virtual environment setup, configuring `.env` credentials, running the CLI (including `--no-cache` and `--fresh-start` flags), and starting the local Flask server for API testing.

3. **[Deployment Guide](docs/DEPLOYMENT.md)**
    * **Audience:** Users deploying the bot on an always-on server (e.g., Raspberry Pi 5).
    * **Content:** Production Docker configurations (`docker-compose.yml`), managing environment variables (`DATA_PATH`, `USER_ID`, etc.), deploying via Docker Compose, updating Docker images automatically, and viewing production logs.

## Core API Endpoints

Once running, the standard base path is `http://localhost:5000/v1/`.

**Crew:**

```bash
# List all crew (id, name, display_name)
curl http://localhost:5000/v1/crew

# Status of Crew Member ID 1 ("Are they available?")
curl http://localhost:5000/v1/crew/1/available

# How long are they available? (e.g. "2.5h")
curl http://localhost:5000/v1/crew/1/duration
```

**Appliances:**

```bash
# Is this engine available based on current manning rules?
curl http://localhost:5000/v1/appliances/P22P6/available

# How long is the engine available?
curl http://localhost:5000/v1/appliances/P22P6/duration
```

## Management

- `docs/`: Guides explaining architectural intent to usage logic.
* `scripts/`: Manual excel debug explorers (for deep inspection).
* `logs/`: Diagnostic and performance logs.
* `tests/`: Automated test suite.
