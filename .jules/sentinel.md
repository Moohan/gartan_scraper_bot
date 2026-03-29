## 2026-03-29 - SQL Injection Prevention via Whitelisting

**Vulnerability:** Dynamic SQL construction using f-strings for table and column identifiers in `api_server.py` and `db_store.py` (Bandit B608).

**Learning:** Database drivers (like `sqlite3`) do not support parameterization for identifiers (table names, column names). Using f-strings or `.format()` for these creates potential injection vectors if the inputs aren't strictly controlled.

**Prevention:** Use a whitelist-based approach to map allowed input strings to hardcoded static queries. For dynamic `IN` clauses, generating placeholders (e.g., `?,?,?`) is safe if the values themselves are parameterized, but requires `# nosec B608` to satisfy static analysis tools.
