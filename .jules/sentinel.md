## 2026-03-22 - Werkzeug DoS Vulnerability (CVE-2026-27199)
**Vulnerability:** Werkzeug < 3.1.6 is vulnerable to a Denial of Service (DoS) attack via specially crafted multipart data.
**Learning:** Even when application code is secure and uses parameterized queries, vulnerabilities can be introduced through underlying framework dependencies.
**Prevention:** Regularly run dependency scanners like `pip-audit` as part of the CI/CD pipeline and keep critical libraries like Flask and Werkzeug updated.
