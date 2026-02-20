## 2025-05-14 - SQL Injection Risk via Table Name Interpolation
**Vulnerability:** Use of f-strings to interpolate table names in SQL queries in `api_server.py` and `db_store.py`.
**Learning:** While identifiers like table names cannot be parameterized in SQLite using standard `?` placeholders, using f-strings for them creates a vulnerability if the variable can be influenced by external input. Even if currently hardcoded, it sets a dangerous pattern.
**Prevention:** Use explicit whitelisting with static SQL strings for each allowed table name.

## 2025-05-14 - Credential Reflection in Authentication Logs
**Vulnerability:** Logging `login_resp.text` on authentication failure in `gartan_fetch.py`.
**Learning:** Authentication responses (especially in ASP.NET apps) may reflect back submitted form fields, including passwords, especially during error states or server-side validation failures.
**Prevention:** Redact sensitive response content in logs. Log only the status code and content length instead of the full body.
