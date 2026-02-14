# Sentinel Security Journal

## 2026-02-14 - Fix SQL Injection in `get_availability`
**Vulnerability:** Potential SQL injection via f-string interpolation of table and column names in SQLite queries.
**Learning:** Using f-strings for SQL identifiers (table/column names) bypasses standard parameterization (`?` placeholders) and can be exploited if the inputs are user-controlled. Even if not directly user-controlled, it triggers static analysis warnings (Bandit B608).
**Prevention:** Use an explicit whitelist of allowed table/column names and use static SQL query strings for each allowed case.
