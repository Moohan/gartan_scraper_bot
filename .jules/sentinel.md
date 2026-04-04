## 2026-04-04 - Static SQL Whitelisting for Dynamic Identifiers
**Vulnerability:** String interpolation (f-strings) used for SQL table names and column identifiers in `get_availability` and `defrag_availability`, and dynamic `IN` clause generation in `check_rules`.
**Learning:** SQLite parameters only support values, not identifiers. Standard project pattern for dynamic identifiers is explicit whitelisting with completely hardcoded query strings to satisfy strict CI/CD security scanners (Bandit B608).
**Prevention:** Avoid any string manipulation for SQL construction; use `if/elif` blocks to select from a set of hardcoded, static query strings.
