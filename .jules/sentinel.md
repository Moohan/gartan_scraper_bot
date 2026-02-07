## 2025-05-22 - [Production Server Hardening]
**Vulnerability:** Use of Flask's development server (`app.run()`) in a production container environment.
**Learning:** Even when `FLASK_ENV` is set to `production`, `app.run()` will still launch the insecure development server. A secondary safeguard in the code and a robust WSGI server (Gunicorn) are necessary layers of defense.
**Prevention:** Always use a WSGI server like Gunicorn for production deployments and add a code-level check to prevent `app.run()` from executing when in production mode.
