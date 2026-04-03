## 2026-04-03 - SQL Injection Prevention for Dynamic Identifiers
**Vulnerability:** SQL Injection (Bandit B608) via f-string interpolation of table and column names in SQL queries.
**Learning:** SQLite parameters (?) only support values, not identifiers like table or column names. Using f-strings for identifiers is a common but dangerous pattern that security scanners like Bandit and Sourcery will flag.
**Prevention:** Use explicit whitelisting combined with hardcoded, static SQL query strings. For dynamic table selection, use an `if/elif` block to choose between fully hardcoded queries rather than constructing the query string dynamically.
