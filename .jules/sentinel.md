## 2026-03-03 - [SQL Injection and Dependency Vulnerabilities]
**Vulnerability:** SQL injection via dynamic table/column names in SQLite queries and a security vulnerability (CVE-2026-27199) in the Werkzeug dependency.
**Learning:** Bandit identifies B608 issues for f-strings in SQL. However, parameterized dynamic IN clauses (using '?' placeholders) are actually secure and should be preferred over complex refactors that risk introducing business logic bugs (like double-counting or breaking function contracts). Sourcery's strictness can lead to over-engineering; comments explaining safety are a valid mitigation.
**Prevention:** Use static SQL strings for structural changes (like table names). Use parameterized IN clauses for collections. maintain regular audits.
