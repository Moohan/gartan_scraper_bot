## 2026-01-31 - Flask dev server in production container
**Vulnerability:** The application was using `app.run()` in the main container entry point (`container_main.py`), which is insecure for production.
**Learning:** Flask's development server is not designed for production and can have security and performance issues.
**Prevention:** Always use a production WSGI server like Gunicorn when deploying in containers, and launch it via `subprocess` if a multi-process orchestrator is needed.
