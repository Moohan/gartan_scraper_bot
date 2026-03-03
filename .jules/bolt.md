## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2025-03-03 - N+1 Query and Connection Overhead in SQLite

**Learning:** The dashboard was suffering from a classic N+1 query problem, fetching availability for each of the 50 crew members individually. Additionally, opening and closing a new SQLite connection for every small query added significant overhead.

**Action:** Use SQL JOINs to fetch related data in a single batch whenever possible. Implement connection reuse within the request lifecycle (e.g., via Flask's `g` object) to minimize the impact of repeatedly opening/closing the database.
