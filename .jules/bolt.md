## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2026-03-30 - Eliminating N+1 Queries and Optimizing Connections

**Learning:** The dashboard route was suffering from an N+1 query bottleneck, fetching availability for each crew member individually. Additionally, database connections were being opened and closed multiple times per request.

**Action:** Use `LEFT JOIN` with a subquery (to handle potential duplicates from overlapping blocks) to fetch all required data in a single query. Implement database connection persistence using Flask's `g` object and `@app.teardown_appcontext` to reduce overhead and ensure connections are reliably closed.
