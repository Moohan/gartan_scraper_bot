## 2026-02-12 - SQL Injection in Dynamic Table Queries
**Vulnerability:** Use of f-strings to interpolate table and column names into SQLite queries.
**Learning:** SQLite (and most SQL drivers) do not support parameterizing table or column names. Using string interpolation for these values creates a SQL injection vector if the input is untrusted. Bandit flags these as B608.
**Prevention:** Use an explicit whitelist of allowed table/column names and map them to static SQL strings.

## 2026-02-12 - Satisfying Strict Security Scanners (Sourcery/Bandit)
**Vulnerability:** Dynamic SQL construction for `IN` clauses using placeholders can still trigger security scanners even if safe.
**Learning:** Tools like Sourcery and Bandit are highly sensitive to any string interpolation or concatenation in SQL query strings. While `# nosec` can suppress Bandit, Sourcery might still block it.
**Prevention:** Refactor the logic to use individual parameterized queries in a loop. This avoids all dynamic SQL construction and satisfies both automated scanners and human reviewers by making the code demonstrably safe.
