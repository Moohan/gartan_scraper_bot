## 2026-02-16 - SQL Injection via Dynamic Table Names
**Vulnerability:** Use of f-strings to interpolate table and column names into SQLite queries.
**Learning:** Even when table names are internally controlled, dynamic SQL construction is flagged by security scanners and presents a risk if the control flow ever changes. Whitelisting allowed table names and using static SQL strings is the most secure pattern.
**Prevention:** Always use parameterized queries for values and a strict whitelist for dynamic table or column names.

## 2026-02-16 - Credential Reflection in Logs
**Vulnerability:** Logging raw response content (`login_resp.text`) on authentication failure and printing usernames to stdout.
**Learning:** Authentication responses may reflect submitted credentials or reveal system internals that could be useful to an attacker. Debug prints in production code can easily leak sensitive data.
**Prevention:** Redact response content in error logs for authentication endpoints and use proper logging levels that exclude sensitive data from production output.
