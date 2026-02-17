## 2026-02-17 - SQL Injection Hardening via Whitelisting
**Vulnerability:** SQL injection when dynamic table or column names are needed in queries, which cannot be parameterized using standard DB-API placeholders.
**Learning:** Bandit (B608) flags any string-based query construction. Parameterization only works for values, not for identifiers like table or column names.
**Prevention:** Use an explicit whitelist with static SQL strings for allowed identifiers. This satisfies static analysis tools and ensures only trusted identifiers are used in queries.
