## 2025-05-15 - [Sensitive Data Logging and Insecure Production Server]
**Vulnerability:** Raw credentials (username/password) were being logged in `gartan_fetch.py`, and the Flask development server was used in production via `container_main.py`.
**Learning:** Legacy debug prints can easily leak secrets if not audited. `app.run()` is a common but dangerous pattern for production containers.
**Prevention:** Use a formal logging framework and strictly audit all log statements for PII/secrets. Enforce the use of a production WSGI server (e.g., Gunicorn) and add code-level safeguards to prevent development servers from starting in production environments.

## 2025-05-15 - [Alpine Docker Build Failure with lxml]
**Vulnerability:** N/A (Build stability/Security consistency)
**Learning:** The `lxml` library requires system-level development packages (`libxml2-dev`, `libxslt-dev`) to build from source on Alpine Linux, and their corresponding runtime libraries for execution.
**Prevention:** Always ensure system-level dependencies are included in the `Dockerfile` for any Python packages that compile C extensions (like `lxml`).
