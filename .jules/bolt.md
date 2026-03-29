## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-03-29 - Dashboard N+1 Query Optimization
**Learning:** The dashboard route was performing N+1 queries by fetching each crew member's availability individually. For 50 crew members, this resulted in 50+ extra database calls. Combining this with a single `LEFT JOIN` and using `flask.g` for connection persistence significantly reduced latency.
**Action:** Always look for N+1 query patterns in routes that display lists of items with related data. Use JOINs or batch fetching to minimize database roundtrips.
