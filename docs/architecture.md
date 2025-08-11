## Architecture Overview

Consolidated active design reference. Historical milestone and deep‑dive docs moved to `docs/archive/`.

### Core Layers
- Fetch: `gartan_fetch.py` – session reuse & intelligent cache
- Parse: `parse_grid.py` – slot → block aggregation
- Store: `db_store.py` – idempotent inserts, historical preservation, reset via `RESET_DB=1`
- Serve: `api_server.py` – availability booleans, duration strings/null, weekly hour aggregation
- Orchestrate: `run_bot.py` / `scheduler.py` – periodic scraping

### Caching Strategy
Historic days (day_offset < 0) use infinite cache; today 15m; tomorrow 60m; future (>=2) 24h. Cleanup uses whole-day age.

### Week Alignment
Fetch always includes Monday of current week forward to guarantee complete weekly metrics.

### Key Endpoints
- Availability: `/v1/crew/<id>/available`, `/v1/appliances/<name>/available`
- Duration: `/v1/crew/<id>/duration`, `/v1/appliances/<name>/duration` → `"3.5h"` or `null`
- Weekly Hours: `/v1/crew/<id>/hours-this-week`, `/v1/crew/<id>/hours-planned-week`

### Database
UTC times; unique indexes prevent duplicate blocks; non‑destructive init unless reset flag set.

### Errors & Health
JSON errors `{ "error": "..." }`; `/health` reports DB data presence.

### Phase 3 (Planned)
Next change times, upcoming durations, crew ↔ appliance mapping.

Historical documents archived to declutter root.
