## 2026-02-04 - Production Server Hardening
**Vulnerability:** Use of Flask development server in a containerized production-like environment.
**Learning:** Container orchestrators often use `multiprocessing.Process` to manage multiple services. While `app.run()` works, it lacks production-grade concurrency and security. Switching to `gunicorn` via `subprocess.run` inside the child process provides a robust WSGI layer while still allowing the orchestrator to manage the lifecycle.
**Prevention:** Enforce a check for `FLASK_ENV` or `FLASK_DEBUG` in the application's entry point and refuse to run the built-in server if production is intended. Ensure `gunicorn` is present in `requirements.txt`.
