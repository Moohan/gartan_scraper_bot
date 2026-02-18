## 2026-02-18 - SQL Injection Hardening with Whitelists
**Vulnerability:** String interpolation (f-strings) of table and column names in SQL queries was flagged by Bandit (B608) as a potential SQL injection vector.
**Learning:** Even when variables are internally constrained, static analysis tools flag dynamic SQL construction. Whitelisting table names and using static SQL strings for each case is a more robust and compliant pattern.
**Prevention:** Avoid f-string interpolation for any part of a SQL query. Use a whitelist mapping or explicit conditional blocks for dynamic table/column names.

## 2026-02-18 - Redacting Sensitive Data in Logs
**Vulnerability:** Logging `login_resp.text` or `schedule_resp.text` on failure could leak credentials, session tokens, or PII if the server echoes them back.
**Learning:** Production logs should never contain raw response bodies from authentication or sensitive AJAX endpoints.
**Prevention:** Explicitly redact or suppress response bodies in error logs for sensitive operations.

## 2026-02-18 - Inline Bandit Suppressions
**Vulnerability:** Separate line `# nosec` comments were being ignored by Bandit or causing warnings.
**Learning:** Bandit directives must be inline on the same line as the code they are suppressing.
**Prevention:** Always place `# nosec BXXX` inline at the end of the line of code.
