## 2026-03-21 - Dependency-level DoS prevention
**Vulnerability:** Werkzeug 3.1.5 was vulnerable to a Denial of Service (DoS) via crafted requests (CVE-2026-27199).
**Learning:** Even when the application code follows secure patterns, underlying framework dependencies can introduce critical vulnerabilities that bypass code-level protections.
**Prevention:** Regularly run automated dependency scans (`pip-audit`) to identify and patch CVEs in third-party libraries.
