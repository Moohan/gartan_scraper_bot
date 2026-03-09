# Sentinel Journal - Critical Security Learnings

## 2026-03-09 - SQL f-string Hardening
**Vulnerability:** Dynamic SQL construction using f-strings for table and column names was flagged by Bandit and Sourcery.
**Learning:** Even when table/column names are from internal logic, f-strings in `execute()` calls are high-risk and trigger security scanners. Refactoring into static query strings within conditional blocks (whitelisting) satisfies scanners and is more robust.
**Prevention:** Use static query strings for any part of the SQL statement that cannot be parameterized (like table/column names), using conditional logic to select the correct hardcoded query.
