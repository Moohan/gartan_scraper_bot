## 2025-05-15 - [Sensitive Data Logging and Insecure Production Server]
**Vulnerability:** Raw credentials (username/password) were being logged in `gartan_fetch.py`, and the Flask development server was used in production via `container_main.py`.
**Learning:** Legacy debug prints can easily leak secrets if not audited. `app.run()` is a common but dangerous pattern for production containers.
**Prevention:** Use a formal logging framework and strictly audit all log statements for PII/secrets. Enforce the use of a production WSGI server (e.g., Gunicorn) and add code-level safeguards to prevent development servers from starting in production environments.
