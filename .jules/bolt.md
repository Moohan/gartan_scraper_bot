## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-18 - Batching and Connection Reuse in SQLite
**Learning:** Reopening SQLite connections in a loop and performing N+1 queries is a major bottleneck in Flask APIs. Reusing connections via `flask.g` and batching data with JOINs significantly reduces latency (measured ~54% improvement).
**Action:** Always prefer batching and connection pooling for high-frequency routes like dashboards.
