## 2026-02-27 - [Dependency Vulnerability and Security Headers]
**Vulnerability:** CVE-2026-27199 (Werkzeug DoS on Windows) and missing defense-in-depth security headers (HSTS, Referrer-Policy).
**Learning:** Outdated dependencies can introduce OS-specific vulnerabilities even if the primary deployment is on Linux. Explicit security headers are often overlooked but provide essential browser-level protections.
**Prevention:** Regularly run `pip-audit` to identify vulnerable packages and maintain a comprehensive set of security headers in the application's response middleware.
