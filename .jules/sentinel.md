## 2026-02-19 - SQL Injection via Whitelist
**Vulnerability:** Use of f-string interpolation for table and column names in SQLite queries.
**Learning:** Even when the variables are controlled by the application, Bandit flags them as high-risk. Using a whitelist of static SQL strings is the preferred pattern for both security and satisfying static analysis tools.
**Prevention:** Avoid any string interpolation in `conn.execute()` calls. Use explicit `if/elif` blocks for dynamic table selection.
