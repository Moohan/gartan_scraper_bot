## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-03-16 - Resolve N+1 and Connection Leaks with g and JOINs

**Learning:** The dashboard route was opening a new SQLite connection for every crew member and every rule check, causing significant overhead and potential file descriptor exhaustion. Using a single JOIN query to fetch all required availability data and persisting the connection in `flask.g` reduced latency by over 50%.

**Action:** Always check for N+1 query patterns in loops that interact with the database. Use Flask's `g` object for request-scoped connection persistence to avoid redundant connection overhead.
