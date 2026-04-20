## 2025-05-14 - Information Disclosure via Verbose Logging

**Vulnerability:** Application logs were capturing full HTTP response bodies from the Gartan AJAX endpoints on failure, which could contain sensitive HTML fragments or session tokens.

**Learning:** Logging the full response text (`response.text`) for debugging failed authenticated requests is a high-risk pattern that leads to unintentional PII/credential exposure in log aggregation systems.

**Prevention:** Always log response metadata (status code, content length) instead of full bodies for authenticated requests. Use structured logging to capture specific non-sensitive error fields if needed.
