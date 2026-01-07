## 2024-07-17 - Don't Break Caching in the Name of Speed

**Learning:** I implemented a major performance improvement by switching to asynchronous fetching, but in the process, I completely broke the existing caching mechanism. This was a critical regression that would have negated the performance gains on subsequent runs and put unnecessary load on the external service.

**Action:** When refactoring for performance, always ensure that existing functionality, especially caching, is preserved. I need to be more careful about the scope of my changes and not get so focused on one aspect of performance that I break another.

## 2024-07-16 - Avoid Redundant BeautifulSoup Parsing

**Learning:** A significant performance anti-pattern was discovered in `parse_grid.py` where the same HTML string was being parsed by BeautifulSoup multiple times within different functions called from a single parent function. Creating a BeautifulSoup object is an expensive operation as it involves building a complete parse tree of the document.

**Action:** For any performance-critical code that involves parsing HTML or XML, I will ensure that the document is parsed only once. The resulting `soup` object should be created in the primary function and then passed as an argument to any helper or child functions that need to inspect or manipulate the document. This avoids the overhead of redundant parsing and can significantly speed up data extraction tasks.
