## 2026-03-07 - Non-interactive CI failure with Safety CLI 3.x
**Vulnerability:** CI/CD pipeline failure (Denial of Service to development flow).
**Learning:** Safety CLI 3.x requires an interactive login or a managed API key. In non-interactive CI environments without valid secrets, it triggers an `EOF when reading a line` error, breaking the build.
**Prevention:** Use `pip-audit` as a more robust, non-interactive alternative for dependency scanning in CI, or ensure `SAFETY_API_KEY` is always present and valid for the environment.
