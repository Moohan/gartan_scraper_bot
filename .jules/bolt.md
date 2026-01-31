## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-01-31 - Batching Database Queries with JOINs

**Learning:** The dashboard route had a classic N+1 query problem where it queried the database for each crew member's availability individually. By introducing a `get_dashboard_data` helper that uses a single SQL `LEFT JOIN`, I reduced the number of queries from ~52 to 2 (for 50 crew members), resulting in a ~76% latency reduction (0.058s -> 0.014s).

**Action:** Always look for loops that perform database queries or API calls and replace them with batch operations or JOINs. Even fast SQLite connections add up when repeated dozens of times per request.
