## 2026-03-15 - Werkzeug Security Upgrade
**Vulnerability:** Werkzeug 3.1.5 was vulnerable to CVE-2026-27199, which could lead to Denial of Service or potentially more severe issues if the debugger was enabled.
**Learning:** Outdated dependencies can introduce critical vulnerabilities even if the application code itself is secure.
**Prevention:** Regularly scan dependencies using tools like `pip-audit` and keep core libraries like Werkzeug and Flask updated to their latest secure versions.
