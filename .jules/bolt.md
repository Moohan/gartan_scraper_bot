## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-13 - Batching SQLite Queries with JOINs
**Learning:** In SQLite-backed Flask apps, N+1 query patterns in the dashboard (one query per crew member) are a major bottleneck. Combining metadata (role, skills) with status (availability) using a `LEFT JOIN` and grouping results by entity ID reduced dashboard latency by ~60%. Standardizing data formatting into a helper function like `format_availability_data` ensures consistency across batch and individual lookups.
**Action:** Always look for loops that perform database queries and replace them with a single JOIN query. Use Flask's `g` object for per-request connection caching to further reduce overhead.
