## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-22 - Batching Queries via JOINs and Connection Reuse

**Learning:** The dashboard route suffered from a classic N+1 query bottleneck because it iterated over crew members and fetched availability individually. Additionally, redundant database lookups were happening in rule checking functions (`check_rules`) even when the required data was already available in the caller's context.

**Action:** Consolidate data fetching using `LEFT JOIN` to retrieve both crew metadata and availability in a single query. Refactor helper functions to accept lists of dictionaries rather than IDs to eliminate redundant internal queries. Implement SQLite connection reuse via Flask's `g` object to minimize connection overhead within a single request.
