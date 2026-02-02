## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-02 - Batching SQLite Queries with JOINs

**Learning:** The dashboard route had a classic N+1 query problem, making a separate database connection and query for every crew member. Using a single `LEFT JOIN` with a subquery (to handle potential multiple availability blocks) significantly reduced overhead.

**Action:** In SQLite-backed applications, prioritize fetching related data in a single query using JOINs rather than iterating over a list of entities and querying for their state individually. This is especially important for dashboard-style views.
