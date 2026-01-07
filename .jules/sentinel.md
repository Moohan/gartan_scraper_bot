## 2024-07-22 - Flask Debug Mode Exposure

**Vulnerability:** The Flask application in `api_server.py` could be launched in debug mode in a production environment by setting the `FLASK_DEBUG` environment variable.

**Learning:** Relying on environment variables to control critical security settings like debug mode is unsafe. If an attacker gains limited access to the deployment environment, they could enable debug mode, which often exposes a web-based console with arbitrary code execution capabilities.

**Prevention:** Critical security flags, especially those that control debugging or expose sensitive information, must be explicitly disabled in code intended for production. For this application, `debug=False` is now hardcoded in the `app.run()` call within `api_server.py` to ensure it can never be overridden by an environment variable.
