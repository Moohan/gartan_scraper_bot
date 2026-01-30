## 2026-01-30 - Hardening API Server with Production Safeguards
**Vulnerability:** Use of Flask's development server (`app.run()`) in production-like orchestration scripts and missing security headers.
**Learning:** Even when `gunicorn` is listed in requirements, orchestrator scripts (like `container_main.py`) might still default to `app.run()`. Explicitly enforcing a production-grade WSGI server and adding a code-level guard against `app.run()` in non-development environments significantly reduces the risk of insecure deployment.
**Prevention:** Always use a WSGI server for production and implement environment-based checks to prevent the development server from starting in production.

## 2026-01-30 - Critical Werkzeug Vulnerability
**Vulnerability:** Werkzeug 3.1.4 is vulnerable to 'Improper Handling of Windows Device Names'.
**Learning:** Dependency pinning is crucial, but keeping them updated to fix known CVEs is equally important. Memory pointed to 3.1.5 as the fix.
**Prevention:** Regularly scan dependencies and update to patched versions (e.g., 3.1.5 for Werkzeug).
