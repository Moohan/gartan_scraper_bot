## 2026-02-06 - API Server Hardening and Production Safeguard
**Vulnerability:** Use of Flask development server (`app.run()`) in production and missing security headers.
**Learning:** Even with an orchestrator like `container_main.py`, the application can still be vulnerable if it calls the development server. Transitioning to Gunicorn via `subprocess.run` with validated environment variables is the secure pattern.
**Prevention:** Always use a production WSGI server for Flask apps and explicitly safeguard the `if __name__ == "__main__":` block against accidental production use.

## 2026-02-06 - Safety 3.x CI Failure
**Vulnerability:** N/A (CI failure)
**Learning:** `safety` version 3.x requires an account/login by default, which causes `EOF` errors in non-interactive CI environments.
**Prevention:** Use `pip-audit` as a more CI-friendly alternative for dependency scanning, or remove `safety` if not configured with an API key.
