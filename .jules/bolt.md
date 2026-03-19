## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-03-05 - SQL JOINs solve N+1 bottlenecks

**Learning:** Replacing an N+1 query loop with a single SQL `LEFT JOIN` significantly reduced dashboard latency (~23% reduction for 50 crew members). Database connection persistence via `flask.g` further eliminated redundant connection overhead.

**Action:** Prefer batching related data into single queries over iterative fetching. Always implement connection persistence in web applications to avoid the cost of repeated handshakes.
