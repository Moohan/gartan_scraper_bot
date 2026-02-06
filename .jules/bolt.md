## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2025-02-05 - Flask+SQLite N+1 Query Optimization
**Learning:** In Flask applications using SQLite, the N+1 query pattern (fetching a list then querying for each item) is particularly expensive because of the overhead of opening/closing connections or even just repeated statement execution. Combining connection reuse via `flask.g` and batching queries with `JOIN` operations resulted in a >50% latency reduction on the dashboard.
**Action:** Always look for loops containing database queries in route handlers and replace them with batch `JOIN` queries. Always implement connection caching in `flask.g` to avoid the overhead of repeated `sqlite3.connect` calls.
