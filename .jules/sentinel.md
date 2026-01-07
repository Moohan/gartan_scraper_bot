## 2024-07-25 - Insecure Flask Debug Mode Activation
**Vulnerability:** The Flask debug mode in `api_server.py` was activated based on the `FLASK_DEBUG` environment variable. This is a security risk because it could be unintentionally enabled in a production environment, exposing sensitive information.

**Learning:** Relying on `FLASK_DEBUG` for enabling debug mode is not a secure practice for production applications. A more robust approach is to tie debug mode to a dedicated environment variable, such as `FLASK_ENV`, which is less likely to be enabled by accident.

**Prevention:** To prevent this issue from recurring, the codebase should consistently use the `FLASK_ENV` environment variable to control debug mode. All production environments should have `FLASK_ENV` explicitly set to `"production"` to ensure debug mode is disabled by default.
