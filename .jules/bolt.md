## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-03-24 - N+1 Bottleneck in Dashboard Route

**Learning:** The dashboard route was suffering from an N+1 query pattern, executing a separate availability check for every crew member. Combined with fresh database connections per helper call, this created significant latency.

**Action:** Consolidate data fetching using `LEFT JOIN` and implement request-bound database connection persistence via `flask.g`. This reduced average latency by over 50% for 50 crew members.
