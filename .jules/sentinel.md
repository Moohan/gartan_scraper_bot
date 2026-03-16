# Sentinel Security Journal

## 2026-03-16 - Werkzeug DoS Vulnerability Fix
**Vulnerability:** CVE-2026-27199 (Denial of Service) found in Werkzeug < 3.1.6.
**Learning:** Even if application code is secure, dependencies can introduce critical risks. Regular scans with `pip-audit` are essential.
**Prevention:** Pin dependencies to secure versions in `requirements.txt` and automate auditing in CI.

## 2026-03-16 - CI Audit Failures with Safety 3.x
**Vulnerability:** N/A (CI Process failure)
**Learning:** Security tools like `safety` 3.x may require interactive authentication or specific API keys, causing CI to hang or fail with EOF errors.
**Prevention:** Use `pip-audit` as a non-interactive alternative for dependency scanning in CI environments to ensure consistent auditing without blocking builds.
