## 2026-03-26 - Hardening SQL and Redacting PII
**Vulnerability:** SQL injection risk (Bandit B608) and PII leakage in debug logs.
**Learning:** Constructing SQL queries using f-strings for table/column identifiers, even with trusted values, triggers security scanners. Explicit whitelisting and static query strings are the preferred project pattern. Redacting usernames from logs is essential for GDPR compliance and general security hygiene.
**Prevention:** Always use static SQL query strings with parameterized values (?). Use `flask.g` for connection management to ensure resource cleanup. Redact sensitive credentials (usernames/passwords) in all log statements.
