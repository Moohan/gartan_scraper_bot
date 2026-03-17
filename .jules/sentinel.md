## 2026-03-17 - Dependency Vulnerability and Security Hardening
**Vulnerability:** Werkzeug 3.1.5 was vulnerable to CVE-2026-27199 (DoS). Multiple Bandit B608 (SQL Injection) and B104 (Hardcoded bind all interfaces) warnings were present. Missing `Referrer-Policy` header.
**Learning:** Even if application code is secure, dependencies can introduce critical vulnerabilities that only `pip-audit` or similar tools can detect. Automated scanners like Bandit often flag dynamic SQL even when variables are internal, necessitating static refactoring for compliance.
**Prevention:** Regular use of `pip-audit` and `bandit`. Prefer static SQL query strings over f-strings for table/column names. Implement defense-in-depth with comprehensive security headers including `Referrer-Policy`.
