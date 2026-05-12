## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2025-05-14 - SQL-Side Sorting and Single-Pass Processing
**Learning:** Shifting sorting logic to the database using ORDER BY with CASE statements and consolidating multiple data processing loops into a single pass significantly improves route efficiency and scalability, even for Python/Flask apps where initial latency is low.
**Action:** Prioritize database-level sorting and filtering. Aim for O(n) data transformation loops that build all required data structures in a single pass over result sets.
