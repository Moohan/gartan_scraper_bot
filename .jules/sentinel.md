# Sentinel Security Journal

## 2026-03-28 - Whitelisting SQL Identifiers
**Vulnerability:** SQL Injection via f-string interpolation of table and column names (Bandit B608).
**Learning:** While values should be parameterized with `?`, SQL identifiers like table names cannot be parameterized. Using f-strings to build these queries triggers security alerts even if the input is internally controlled.
**Prevention:** Use explicit whitelisting and hardcoded static query strings to handle dynamic table selection. This satisfies static analysis tools and provides defense in depth.
