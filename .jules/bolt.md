## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-10 - Solving N+1 query patterns with JOINs and Batching

**Learning:** The dashboard route suffered from a significant N+1 query problem, fetching availability individually for each crew member. Combining these into a single `LEFT JOIN` query and batching data for business rule checks reduced latency by ~57% (from ~27ms to ~11ms). Additionally, using `flask.g` for per-request connection caching prevents the overhead of repeatedly opening/closing SQLite connections.

**Action:** Always audit routes that iterate over lists for nested database calls. Prioritize `JOIN`s or batch lookups (using `IN` clauses) and leverage application-level request context for resource caching.

## 2026-02-10 - Avoiding Redundant HTML Parsing

**Learning:** Parsing large HTML strings with BeautifulSoup is CPU-intensive. In `parse_grid.py`, the same grid HTML was being parsed three separate times for crew, appliances, and skills. Consolidating this into a single `BeautifulSoup` object shared across sub-parsers significantly reduces the scraping latency. Additionally, using `lxml` provides a measurable speedup over `html.parser`.

**Action:** When a single source document needs to be queried by multiple components, parse it once at the entry point and pass the resulting DOM object down. Always provide a fallback parser (like `html.parser`) to ensure robustness if the preferred fast parser (like `lxml`) is unavailable.
