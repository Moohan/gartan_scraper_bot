## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2025-02-20 - SQLite N+1 and Connection Overhead in Flask

**Learning:** In high-frequency routes like the dashboard, opening a new SQLite connection for every small data fetch (like availability for each crew member) and performing individual queries (N+1) creates significant latency.

**Action:** Implement connection reuse via `flask.g` to maintain a single connection per request. Use `LEFT JOIN` to batch fetch metadata and status in a single query to drastically reduce database round-trips.
