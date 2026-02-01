## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2025-01-24 - Resolve N+1 Queries with SQL JOINs

**Learning:** The dashboard endpoint was experiencing an N+1 query problem, fetching crew members first and then querying availability for each one individually. This resulted in significant latency as the crew size grew. Using a single `LEFT JOIN` to fetch both crew details and current availability in one batch reduced latency by ~50%.

**Action:** Always look for loops that perform database queries and attempt to consolidate them into a single JOIN or batch query.

## 2025-01-24 - lxml is a Hard Dependency for BeautifulSoup

**Learning:** The test suite was failing due to a missing `lxml` parser, even though `beautifulsoup4` was installed. `BeautifulSoup(html, "lxml")` requires the `lxml` package explicitly.

**Action:** Ensure all parser libraries used by BeautifulSoup (like `lxml`) are explicitly listed in `requirements.txt`.
