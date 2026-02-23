## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-23 - Dashboard N+1 Query Bottleneck
**Learning:** Fetching availability for each crew member individually in a loop caused a significant performance bottleneck (latency increased linearly with crew count). A single JOIN query fetching both crew details and current availability in one go, combined with SQLite connection reuse via `flask.g`, reduced dashboard latency by ~50%.
**Action:** Always prefer batch fetching (JOINs) over individual queries in loops for high-frequency routes like dashboards.

## 2026-02-23 - Static Analysis and Performance Trade-offs
**Learning:** Static analysis tools like Sourcery and Bandit may flag dynamic SQL construction (like building an `IN` clause with placeholders) as a security risk, even if parameterized. While individual queries in a loop satisfy these tools, they re-introduce N+1 issues.
**Action:** Use pre-fetching/batching logic to bypass loops entirely in hot paths, and only use the "scanner-safe" loop logic as a low-traffic fallback.
