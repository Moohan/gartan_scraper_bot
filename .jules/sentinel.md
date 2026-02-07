## 2025-05-22 - [Production Server Hardening]
**Vulnerability:** Use of Flask's development server (`app.run()`) in a production container environment.
**Learning:** Even when `FLASK_ENV` is set to `production`, `app.run()` will still launch the insecure development server. A secondary safeguard in the code and a robust WSGI server (Gunicorn) are necessary layers of defense.
**Prevention:** Always use a WSGI server like Gunicorn for production deployments and add a code-level check to prevent `app.run()` from executing when in production mode.

## 2025-05-22 - [CI/CD Security Tooling Constraints]
**Vulnerability:** Inconsistent dependency scanning and build failures in CI.
**Learning:** `safety` version 3+ requires user registration, making it unsuitable for non-interactive CI environments without API keys. Additionally, Alpine-based Docker builds for `lxml` require system-level development libraries (`libxml2-dev`, `libxslt-dev`) that are not present by default.
**Prevention:** Prefer `pip-audit` for open-source dependency scanning in CI. Ensure Dockerfiles for Alpine include all necessary build-time and runtime libraries for binary-heavy packages like `lxml`.
