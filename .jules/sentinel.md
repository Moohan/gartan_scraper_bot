## 2026-03-18 - [Dependency Hardening]
**Vulnerability:** CVE-2026-27199 (Denial of Service) in Werkzeug 3.1.5.
**Learning:** Even if the application logic is secure, underlying dependencies can introduce critical vulnerabilities that can only be resolved by upgrading the package.
**Prevention:** Regularly run `pip-audit` and keep dependencies updated to their latest security-patched versions.

## 2026-03-18 - [SQL Injection Prevention]
**Vulnerability:** Bandit B608 (Hardcoded SQL expressions) flagged f-string interpolation for table and column names.
**Learning:** Static analysis tools like Bandit are strict about any dynamic SQL construction, even when table/column names are internal constants. Whitelisting via hardcoded query strings in conditional blocks is the preferred way to satisfy these tools and ensure safety.
**Prevention:** Avoid f-strings for SQL query construction. Use hardcoded static strings within `if/else` blocks for dynamic table or column selection.
