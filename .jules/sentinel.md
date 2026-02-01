## 2026-02-01 - Production Safeguard and Secure Orchestration

**Vulnerability:** Use of Flask's development server (`app.run()`) in production-like container environments.
**Learning:** Even if a production server like Gunicorn is installed, it won't be used unless the entry point orchestrator is explicitly configured to invoke it. Relying on `app.run()` in a multi-process orchestrator (`container_main.py`) bypasses the security and performance benefits of a real WSGI server.
**Prevention:** 1. Implement a fail-fast safeguard in `api_server.py` that checks `FLASK_ENV` and refuses to start the dev server in production. 2. Update the container orchestrator to dynamically switch between the dev server and Gunicorn based on the environment.
