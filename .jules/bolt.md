## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-11 - [Dashboard N+1 Query Optimization]
**Learning:** The dashboard route was suffering from an N+1 query problem, making a separate database call for each crew member's availability. This scaled poorly with the number of crew members.
**Action:** Use a single SQL query with a `LEFT JOIN` and `GROUP BY` to fetch crew members and their most recent availability status in one batch. Additionally, cache the SQLite connection in Flask's `g` object to avoid connection overhead within a single request.
