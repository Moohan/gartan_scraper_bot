## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2025-01-03 - SQLite N+1 Bottleneck in Dashboard

**Learning:** In Flask/SQLite apps with complex relationship metadata (roles/skills), individual queries per list item are the primary latency driver. Reusing connections via `flask.g` and batching with `LEFT JOIN` provides the highest ROI for performance.

**Action:** Always check the `root` dashboard route for N+1 query patterns before attempting micro-optimizations.
