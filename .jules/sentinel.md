# Sentinel Journal - Critical Security Learnings

This journal records CRITICAL security learnings found during Sentinel's mission.

## 2026-02-26 - Hardening Dynamic SQL and Credential Logging
**Vulnerability:** Use of f-strings for dynamic SQL table/column names and plain-text credential logging.
**Learning:** Even internal variables (like table names) should be whitelisted/static to prevent any risk of injection and satisfy security scanners. Debug logs are often overlooked as a source of credential leakage.
**Prevention:** Always use whitelisted conditional branches for dynamic SQL components that cannot be parameterized. Redact all credentials in logs, even in debug mode.
