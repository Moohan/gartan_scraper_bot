## 2026-03-05 - Security Audit and Hardening
**Vulnerability:**
1. CVE-2026-27199: Werkzeug Path Traversal vulnerability in `safe_join` on Windows.
2. SQL Injection: Use of f-strings for table and column names in SQL queries in `api_server.py` and `db_store.py`.
3. Credential Exposure: Debug print in `gartan_fetch.py` logging Gartan credentials.
4. Information Disclosure: Logging full response bodies on error in `gartan_fetch.py`, and missing `Referrer-Policy` header.

**Learning:**
- Dynamic SQL construction using f-strings, even for internal names like table names, is flagged by security scanners (Bandit B608) and should be avoided in favor of static strings or explicit mapping.
- Debug prints used for troubleshooting can easily be left in code, leaking sensitive environment variables like `GARTAN_USERNAME`.
- Dependency vulnerabilities (like in Werkzeug) can be identified using `pip-audit` and should be addressed promptly.

**Prevention:**
- Use `pip-audit` and `bandit` regularly in CI/CD.
- Always use parameterized queries for data and static strings for schema elements.
- Ensure debug logging redacts sensitive information and avoid `print()` for debugging in production code.
- Implement comprehensive security headers by default.
