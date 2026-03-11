## 2026-03-11 - SQL Hardening and Log Redaction
**Vulnerability:** SQL injection vectors via f-string interpolation and sensitive data exposure in application logs.
**Learning:** Even when table names are controlled internally, using f-strings for SQL identifiers is flagged by scanners and sets a poor precedent. Full response bodies in logs can accidentally leak session data or PII during fetch failures.
**Prevention:** Refactor dynamic SQL identifiers into static strings within conditional blocks. Redact full response bodies in logs, recording only content length for debugging purposes.
