## 2026-02-12 - SQL Injection in Dynamic Table Queries
**Vulnerability:** Use of f-strings to interpolate table and column names into SQLite queries.
**Learning:** SQLite (and most SQL drivers) do not support parameterizing table or column names. Using string interpolation for these values creates a SQL injection vector if the input is untrusted. Bandit flags these as B608.
**Prevention:** Use an explicit whitelist of allowed table/column names and map them to static SQL strings. If a dynamic `IN` clause is necessary, construct the placeholder string (`?,?,?`) safely and use `# nosec B608` to satisfy static analysis while documenting the safety.
