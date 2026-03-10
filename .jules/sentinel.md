## 2026-03-10 - Refactoring Dynamic SQL to Static Queries
**Vulnerability:** SQL Injection risk from f-string interpolation of table/column names.
**Learning:** Even when table names are from internal constants, security scanners (Bandit, Sourcery) flag them as high risk. Refactoring to static strings within conditional blocks satisfies scanners and follows defense-in-depth.
**Prevention:** Avoid f-strings for SQL query construction; use static strings with conditionals for dynamic table/column selection.
