# Sentinel Security Journal

## 2026-02-14 - Fix SQL Injection in `get_availability`
**Vulnerability:** Potential SQL injection via f-string interpolation of table and column names in SQLite queries.
**Learning:** Using f-strings for SQL identifiers (table/column names) bypasses standard parameterization (`?` placeholders) and can be exploited if the inputs are user-controlled. Even if not directly user-controlled, it triggers static analysis warnings (Bandit B608).
**Prevention:** Use an explicit whitelist of allowed table/column names and use static SQL query strings for each allowed case.

## 2026-02-14 - CI/CD Robustness and environment fixes
**Vulnerability:** Application crash (`AttributeError`) when authentication fails or credentials are missing.
**Learning:** Defensive programming is essential in core components. If authentication fails, the session object might be `None`, and subsequent calls to its methods will crash the application. Additionally, dependency management (`lxml`) needs proper system libraries in specialized environments like Alpine.
**Prevention:** Always check if optional or external objects (like `session`) are valid before use. Ensure multi-stage Docker builds include both build-time and runtime system dependencies for C-extensions.
