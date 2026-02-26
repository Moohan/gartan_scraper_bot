## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2024-05-15 - Batch Queries and Connection Reuse for High-Frequency Routes

**Learning:** High-frequency routes like the dashboard suffer from N+1 query bottlenecks and repeated database connection overhead. Using `LEFT JOIN` to batch data fetching and `flask.g` for connection reuse significantly reduces latency. In this case, average response time dropped from ~32.5ms to ~13.2ms (approx 60% improvement).

**Action:** Always look for N+1 query patterns in list-based views and prefer JOINs or batch fetching. Implement connection pooling or reuse for database-heavy applications.
