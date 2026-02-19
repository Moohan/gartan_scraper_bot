## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-19 - SQLite Batching and Parser Optimization
**Learning:** Batching SQLite queries via JOINs and using the `lxml` parser instead of `html.parser` significantly reduced API latency by ~55%. Providing a robust fallback for optional dependencies like `lxml` ensures CI/CD stability across different environments.
**Action:** Always prefer JOINs over N+1 query patterns in dashboard routes, and ensure parser-specific code includes a standard library fallback.
