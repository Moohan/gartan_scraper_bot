## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-28 - Dashboard N+1 Query Optimization
**Learning:** The dashboard route was suffering from an N+1 query pattern, where each crew member's availability was fetched in a separate database query. By using a single `LEFT JOIN` query, I reduced the overhead significantly. Additionally, reusing the database connection within the request context using Flask's `g` object further improved performance by avoiding repeated connection initialization.
**Action:** Always look for loops that perform database queries and try to batch them using JOINs or `IN` clauses. Leverage framework-specific context locals (like Flask's `g`) to manage resource lifecycles efficiently.
