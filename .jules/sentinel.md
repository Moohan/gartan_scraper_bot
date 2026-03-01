## 2026-03-01 - Suppressing B608 for Controlled Dynamic SQL
**Vulnerability:** Bandit flags B608 (SQL injection) for any f-string used in `conn.execute()`, even if the values are internally controlled (e.g., hardcoded table names or safely generated placeholders).
**Learning:** In SQLite, certain identifiers like table names cannot be parameterized. When these are dynamic but whitelisted, Bandit still triggers a medium-severity warning. Similarly, generating `?` placeholders dynamically for `IN` clauses triggers B608.
**Prevention:** Use inline `# nosec B608` comments to suppress these specific cases after verifying the interpolation only involves trusted, internally-derived strings. Always add a test case to verify that these endpoints remain secure and functional.
