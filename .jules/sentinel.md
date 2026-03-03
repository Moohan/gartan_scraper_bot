## 2026-03-03 - [SQL Injection and Dependency Vulnerabilities]
**Vulnerability:** SQL injection via dynamic table/column names in SQLite queries and a security vulnerability (CVE-2026-27199) in the Werkzeug dependency.
**Learning:** Bandit identified multiple B608 issues where f-strings were used to construct SQL queries, even when the variables were internally sourced (like table names). Additionally, pip-audit identified a known vulnerability in Werkzeug.
**Prevention:** Use static SQL strings with conditional logic for structural query changes (like table names) instead of string interpolation. Maintain regular dependency audits using pip-audit.
