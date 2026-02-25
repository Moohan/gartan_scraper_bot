## 2026-02-25 - Information Disclosure in Logs
**Vulnerability:** The application was logging full HTTP response bodies from the Gartan system on failure, which could contain session tokens, internal state, or PII. It also logged usernames and authenticated session cookies in debug mode.
**Learning:** Third-party system responses often contain sensitive data that shouldn't be persisted in application logs. Debug logging of session state (cookies) is a common but dangerous pattern.
**Prevention:** Always redact PII (like usernames) in logs. On failure, log metadata like response status and body length instead of the full body. Remove or redact cookie/session logging in production-ready code.
