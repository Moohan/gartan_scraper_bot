## 2026-02-08 - [Credential Leak in Debug Logs]
**Vulnerability:** The application was logging the GARTAN_USERNAME in plain text during the login process via a `print` statement intended for "temporary debug".
**Learning:** Even "temporary" debug prints can be committed and persist in a codebase, leading to sensitive data exposure in production logs.
**Prevention:** Never use `print` for debugging sensitive credentials; use a proper logging framework with sensitive data filtering, and always remove debug-only code before committing.

## 2026-02-08 - [Insecure Production Server Entrypoint]
**Vulnerability:** The container orchestrator (`container_main.py`) was using Flask's development server (`app.run()`) for the production API, which is insecure and not designed for production use.
**Learning:** It's common for developers to use `app.run()` during development and forget to switch to a production WSGI server like Gunicorn for deployment.
**Prevention:** Implement a hard safeguard in the application code that prevents `app.run()` from starting if a production environment variable is set, and ensure the production deployment configuration (Dockerfile/orchestrator) explicitly uses a production-grade server.
