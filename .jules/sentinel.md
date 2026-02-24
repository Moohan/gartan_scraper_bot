## 2026-02-24 - SQL Injection and Sensitive Data Leakage in Logs
**Vulnerability:**
1. Potential SQL injection in `get_availability` due to f-string interpolation of table/column names.
2. Exposure of `username` and full HTML response bodies (potentially containing reflected credentials) in debug and error logs.

**Learning:**
1. Bandit (B608) correctly flags string interpolation in SQL queries. While parameterization (using `?`) is the standard fix for values, table and column names cannot be parameterized in SQLite. Whitelisting is the secure alternative.
2. Logging `response.text` on failure is a common debugging pattern that can accidentally leak sensitive data if the server reflects inputs or includes session tokens in the response body.

**Prevention:**
1. Use explicit, static SQL queries based on a whitelist of allowed table/column names.
2. Redact credentials in logs and use `len(response.text)` instead of the full content for error logging of sensitive endpoints.
