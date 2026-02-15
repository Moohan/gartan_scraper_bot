## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-15 - Batching Queries and JOINs for Dashboard Optimization
**Learning:** The dashboard route had a classic N+1 query problem, fetching availability for each crew member individually. By using a single LEFT JOIN with MAX(ca.end_time) and GROUP BY c.id, I reduced the number of queries from N+3 to 3.
**Action:** Always look for N+1 patterns in routes that render lists. Use SQL JOINs to fetch related metadata and status in a single pass to minimize database round-trip latency.
