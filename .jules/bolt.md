## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2025-02-21 - Batching and Connection Reuse in SQLite

**Learning:** Combining SQLite connection reuse via `flask.g` with JOIN-based batching for N+1 query patterns yielded a ~55% reduction in dashboard latency (24ms -> 11ms). Even though SQLite is local and fast, the overhead of 50+ connection open/close cycles and individual queries is significant.

**Action:** Always prefer batching with JOINs and centralizing connection management in Flask apps to avoid repeated overhead in high-frequency routes.
