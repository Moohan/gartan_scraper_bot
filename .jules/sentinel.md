# Sentinel Journal - Security Learnings

## 2026-02-10 - Gunicorn and Production Safeguards
**Vulnerability:** Use of Flask's development server (`app.run()`) in production via `container_main.py`.
**Learning:** Even if `gunicorn` is in `requirements.txt`, the container entrypoint or orchestrator might still be using the development server.
**Prevention:** Always check the production startup scripts (like `container_main.py` or `docker-compose.yml`) and implement a safeguard in the app itself that prevents `app.run()` if `FLASK_ENV=production`.

## 2026-02-10 - Hardened Security Headers
**Vulnerability:** Missing HSTS, Referrer-Policy, and permissive Content-Security-Policy.
**Learning:** Default Flask `after_request` headers often miss critical security layers like HSTS and strict CSP.
**Prevention:** Standardize a comprehensive set of security headers for all Flask projects in this repository.
