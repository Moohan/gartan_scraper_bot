## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-03-07 - SQLite N+1 and Connection Overhead in Flask

**Learning:** Resolving N+1 queries in the main dashboard via a `LEFT JOIN` and implementing database connection sharing using `flask.g` provided a massive (~57%) performance boost. Even with a local SQLite database, the overhead of opening/closing connections for every helper call and executing individual queries for 50+ entities adds up significantly.

**Action:** Always look for N+1 query patterns in routes that render lists of entities. Use JOINs for metadata and current status. Leverage Flask's `g` object for request-scoped connection persistence to minimize handshake overhead.
