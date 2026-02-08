## 2026-02-08 - [Credential Leak in Debug Logs]
**Vulnerability:** The application was logging the GARTAN_USERNAME in plain text during the login process via a `print` statement intended for "temporary debug".
**Learning:** Even "temporary" debug prints can be committed and persist in a codebase, leading to sensitive data exposure in production logs.
**Prevention:** Never use `print` for debugging sensitive credentials; use a proper logging framework with sensitive data filtering, and always remove debug-only code before committing.

## 2026-02-08 - [Insecure Production Server Entrypoint]
**Vulnerability:** The container orchestrator (`container_main.py`) was using Flask's development server (`app.run()`) for the production API, which is insecure and not designed for production use.
**Learning:** It's common for developers to use `app.run()` during development and forget to switch to a production WSGI server like Gunicorn for deployment.
**Prevention:** Implement a hard safeguard in the application code that prevents `app.run()` from starting if a production environment variable is set, and ensure the production deployment configuration (Dockerfile/orchestrator) explicitly uses a production-grade server.

## 2026-02-08 - [Unchecked Optional Session leading to DoS]
**Vulnerability:** The `gartan_login_and_get_session` function could return `None` on authentication failure, but callers were not checking for `None` before using it, leading to an `AttributeError` and application crash (DoS).
**Learning:** Robustness and security are linked; a failure in a security component (auth) shouldn't cause the entire application to crash due to poor error handling.
**Prevention:** Always check if a session object is valid before attempting to use it, especially when it originates from a function that can fail due to external factors like authentication or network issues.
