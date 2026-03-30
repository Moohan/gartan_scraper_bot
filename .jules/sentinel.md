## 2026-03-30 - SQL Injection via Dynamic Identifiers
**Vulnerability:** Use of f-strings to dynamically insert table and column names into SQL queries (`B608:hardcoded_sql_expressions`).
**Learning:** SQLite parameters (`?`) only work for values, not identifiers (tables/columns). Using f-strings for identifiers is a common pattern that security scanners flag as a potential injection vector.
**Prevention:** Use an explicit whitelist with hardcoded query strings for allowed identifiers. For dynamic `IN` clauses on small datasets, consider fetching and filtering in Python to satisfy strict CI scanners like Sourcery.
