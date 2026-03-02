## 2026-03-02 - SQL Injection Defense in Depth
**Vulnerability:** Possible SQL injection via f-string construction for table and column names in SQLite queries.
**Learning:** Using f-strings to construct SQL queries, even for "internal" metadata like table names, is a dangerous pattern that triggers static analysis tools (Bandit B608) and creates a fragile security posture. Stricter tools like Sourcery also block any string concatenation in SQL execution calls to prevent bypasses.
**Prevention:** Use explicit mapping and static SQL strings for dynamic table/column selection. Avoid any string formatting or concatenation when building query strings. Use parameterized queries for all data values.

## 2026-03-02 - Windows-specific Path Traversal in Werkzeug
**Vulnerability:** CVE-2026-27199 in Werkzeug < 3.1.6 allowed path traversal/DoS on Windows using reserved device names (e.g., NUL) in multi-segment paths.
**Learning:** Security helpers like `safe_join` can have subtle platform-specific bypasses that persist even after initial hardening. Vulnerabilities can exist in core dependencies that are not immediately obvious without specialized scanning.
**Prevention:** Maintain a regular schedule for dependency auditing using tools like `pip-audit` and prioritize patching critical/high CVEs by pinning to fixed versions.
