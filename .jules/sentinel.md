## 2026-03-04 - Static SQL for Dynamic Table Queries
**Vulnerability:** SQL injection risk when using f-strings to interpolate table or column names in database queries, even if the source is internal logic.
**Learning:** Tools like Bandit and Sourcery flag any string interpolation in SQL execution. While parameterized values are safe, table/column names cannot be parameterized in SQLite.
**Prevention:** Use explicit `if/else` logic to select from a set of hardcoded, static SQL query strings when the target table or column is dynamic but known. This satisfies security scanners and provides defense-in-depth.
