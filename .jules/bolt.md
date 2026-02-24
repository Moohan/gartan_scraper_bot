## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2025-02-24 - Batch Queries and Connection Reuse

**Learning:** The dashboard route was suffering from a classic N+1 query problem and significant overhead from opening/closing SQLite connections for every query. By implementing a single JOIN-based query for 50 crew members and using `flask.g` for connection reuse, average response latency was reduced from ~22.5ms to ~11.4ms (a ~50% improvement).

**Action:** Always prioritize batching database queries (JOINs) and connection pooling in high-frequency routes. Use `flask.g` to maintain a single connection per request lifecycle.

## 2025-02-24 - Performance Refactors and Defensive Checks

**Learning:** When refactoring core logic (like scraping or fetching) for performance, it's easy to bypass safety checks that handle failure states (like authentication failures). An `AttributeError` was introduced because the optimized path assumed a valid session object was always present.

**Action:** Ensure all execution paths, especially those optimized for speed, maintain robust error handling and null-checks for external resources (like sessions).
