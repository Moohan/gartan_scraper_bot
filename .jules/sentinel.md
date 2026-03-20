## 2026-03-20 - Dependency Security and Information Leakage
**Vulnerability:** Werkzeug 3.1.5 had a DoS vulnerability (CVE-2026-27199). Additionally, `gartan_fetch.py` was logging the `username` and full response bodies of failed login attempts, potentially exposing sensitive data.
**Learning:** Third-party dependency vulnerabilities can introduce risks even if application code is secure. Debugging code (like print statements) often survives into production and can leak PII or session data.
**Prevention:** Regularly run `pip-audit` to catch dependency vulnerabilities. Implement a strict "no logging of sensitive data" policy and use log redaction for response bodies from authentication providers.
