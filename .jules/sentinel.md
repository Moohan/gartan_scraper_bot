## 2026-02-03 - Production Safeguard and WSGI Server Migration
**Vulnerability:** The application was using Flask's built-in development server (`app.run()`) in the container entry point (`container_main.py`), which is insecure and not performance-optimized for production.
**Learning:** Even if a production-grade WSGI server like Gunicorn is present in `requirements.txt`, developers might still default to `app.run()` in orchestrator scripts. A runtime safeguard in the API server is necessary to enforce the use of a secure server in production environments.
**Prevention:** Implement a check for `FLASK_ENV=production` in `api_server.py` to block the development server, and explicitly configure the orchestrator to launch the application using Gunicorn.

## 2026-02-03 - lxml build dependencies in CI/Docker
**Vulnerability:** Not a direct vulnerability, but a build failure caused by adding a secure/robust parser (`lxml`) without corresponding system dependencies.
**Learning:** Python packages that compile C extensions (like `lxml`) often require system-level development libraries (`libxml2-dev`, `libxslt-dev`) which are not present by default on minimal images (Alpine) or CI runners.
**Prevention:** Always ensure that `Dockerfile` and CI workflows (`.github/workflows/*.yml`) are updated to install necessary system dependencies before running `pip install`.
