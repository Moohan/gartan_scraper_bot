## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-02-17 - Connection Overhead in Loops
**Learning:** Calling `get_db()` (which creates a new `sqlite3` connection) inside a loop (e.g., for each crew member) is a major performance bottleneck. Reusing a single connection for the entire request lifecycle and batching queries with JOINs is much more efficient.
**Action:** Always prefer batch queries with JOINs over individual queries in a loop, and pass the active database connection to helper functions instead of letting them create their own.
