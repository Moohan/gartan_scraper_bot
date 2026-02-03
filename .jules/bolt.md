## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-03-02 - Resolve N+1 Queries with SQL JOINs
**Learning:** The dashboard endpoint was experiencing an N+1 query problem, where it would fetch all crew members and then perform a separate database query for each member's availability. This resulted in a linear increase in response time as the number of crew members grew.
**Action:** Use SQL JOINs to fetch all required data in a single query when rendering lists. This reduced dashboard latency by ~50% in this codebase.
