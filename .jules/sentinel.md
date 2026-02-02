## 2026-02-02 - Flask Development Server in Production
**Vulnerability:** The application was using `app.run()` in `container_main.py`, which is Flask's built-in development server, not suitable for production.
**Learning:** In a multi-process container setup, it's easy to overlook the server entry point.
**Prevention:** Always use a production WSGI server like `gunicorn` and add a safeguard in `app.run` to prevent it from starting if `FLASK_ENV=production`.

## 2026-02-02 - BeautifulSoup Parser Dependency
**Vulnerability:** Tests failed because `lxml` was not installed, despite BeautifulSoup being configured to use it.
**Learning:** BeautifulSoup's behavior depends on the available parsers, and `lxml` is often preferred for performance and consistency.
**Prevention:** Pin the specific parser library (e.g., `lxml==5.1.0`) in `requirements.txt` if it's explicitly used in the code.
