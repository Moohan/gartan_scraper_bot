## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2024-07-20 - Batching Queries and Connection Reuse

**Learning:** In Flask/SQLite applications, opening a new connection for every helper function and querying in loops (N+1) are significant latency bottlenecks. Reusing a single connection per request via `flask.g` and using `JOIN` for batch fetching metadata + availability reduced dashboard latency by ~15-60%.

**Action:** Always check for N+1 query patterns in high-traffic routes and implement connection reuse to minimize SQLite overhead.
