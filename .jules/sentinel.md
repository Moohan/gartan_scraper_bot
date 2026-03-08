# Sentinel's Journal - Critical Security Learnings

## 2026-03-08 - Sensitive Data Leakage in Logs and Console
**Vulnerability:** Debug print statements and verbose error logging were exposing usernames and full response bodies (potentially containing session info or internal details) during authentication failures.
**Learning:** "Temporary" debug code often persists into production environments. Default error logging that captures entire response objects can inadvertently leak sensitive data.
**Prevention:** Always redact sensitive fields in logs. Log content lengths or status codes instead of full bodies for non-API responses. Use a structured logging approach that explicitly handles sensitive data.
