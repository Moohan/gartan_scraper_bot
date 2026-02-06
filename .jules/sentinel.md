## 2026-02-06 - API Server Hardening and Production Safeguard
**Vulnerability:** Use of Flask development server (`app.run()`) in production and missing security headers.
**Learning:** Even with an orchestrator like `container_main.py`, the application can still be vulnerable if it calls the development server. Transitioning to Gunicorn via `subprocess.run` with validated environment variables is the secure pattern.
**Prevention:** Always use a production WSGI server for Flask apps and explicitly safeguard the `if __name__ == "__main__":` block against accidental production use.
