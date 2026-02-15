## 2026-02-15 - SQL Injection and Credential Exposure
**Vulnerability:** SQL injection in `get_availability` via dynamic table names and credential exposure in logs in `gartan_fetch.py`.
**Learning:** Dynamic table names in SQL queries cannot be parameterized directly in SQLite, leading to f-string interpolation which is flagged by Bandit. Additionally, "temporary" debug print statements can easily be left in code, exposing sensitive environment variables like usernames.
**Prevention:** Use an explicit whitelist or hardcoded query mapping for dynamic table/column names. Ensure all debug logging is removed or uses proper logging levels that are not enabled in production.
