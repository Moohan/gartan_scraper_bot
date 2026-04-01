## 2026-04-01 - SQL Injection via Identifier Interpolation
**Vulnerability:** SQL injection vulnerabilities were identified where table names and column names were being interpolated into SQL strings using f-strings (e.g., `f"SELECT ... FROM {table} WHERE {col} = ?"`).
**Learning:** SQLite parameters (?) can only be used for values, not for identifiers like table or column names. Standard parameterized queries do not protect against injection when identifiers are dynamic.
**Prevention:** Use explicit whitelisting to validate dynamic identifiers against a set of allowed values, and use hardcoded query strings for each allowed case. Avoid dynamic SQL construction for identifiers whenever possible.
