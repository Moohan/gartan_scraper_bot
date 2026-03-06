# Sentinel Security Journal

## 2026-03-06 - Path Traversal in Werkzeug & Privacy Enhancement
**Vulnerability:** CVE-2026-27199: Path traversal in Werkzeug's `safe_join` function on Windows.
**Learning:** Outdated dependencies in `requirements.txt` can introduce critical vulnerabilities even if the specific function is not explicitly used in the codebase. Static analysis and dependency auditing are essential.
**Prevention:** Regularly run `pip-audit` and maintain a `Referrer-Policy` to prevent sensitive URL leakage.
