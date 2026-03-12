# Sentinel Security Journal

## 2026-03-12 - SQL Injection Hardening in Dynamic Queries
**Vulnerability:** SQL injection vector through string-based query construction using f-strings for table or column names.
**Learning:** Static analysis tools like Sourcery and Bandit flag any f-string interpolation in SQL as high risk, even if the variables are internally mapped. The repository preference is to refactor these into hardcoded static strings within conditional blocks where table/column names are known literals.
**Prevention:** Avoid dynamic SQL string construction for schema elements (tables, columns). Use explicit conditional logic to select from a set of predefined static query strings.
