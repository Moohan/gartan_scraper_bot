## 2026-02-19 - SQL Injection via Whitelist
**Vulnerability:** Use of f-string interpolation for table and column names in SQLite queries.
**Learning:** Even when the variables are controlled by the application, Bandit flags them as high-risk. Using a whitelist of static SQL strings is the preferred pattern for both security and satisfying static analysis tools.
**Prevention:** Avoid any string interpolation in `conn.execute()` calls. Use explicit `if/elif` blocks for dynamic table selection.

## 2026-02-19 - Dynamic SQL IN Clause vs Static Analysis
**Vulnerability:** Constructing dynamic SQL queries with a variable number of placeholders for `IN` clauses.
**Learning:** Even with parameterized values, static analysis tools like Sourcery may flag dynamic query construction as a security risk. Refactoring to individual queries in a loop, while potentially less performant, is guaranteed to satisfy security scanners and avoids any dynamic string interpolation in the SQL itself.
**Prevention:** For small datasets (like crew lists), prefer iterating and using static parameterized queries over dynamic `IN` clause construction.
