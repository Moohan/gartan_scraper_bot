## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-12 - Optimize SQLite N+1 Queries with LEFT JOINs
**Learning:** The dashboard and appliance routes were suffering from N+1 query patterns, fetching crew data first and then querying availability per member. Using a single SQL query with `LEFT JOIN` and `GROUP BY` to fetch all crew members along with their latest availability reduced dashboard latency by ~55%.
**Action:** Always check for loops that perform database queries. Prefer batching lookups or using JOINs to combine metadata with status information in a single round-trip.
