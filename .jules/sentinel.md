# Sentinel Security Journal

This journal records critical security learnings and patterns discovered in the Gartan Scraper Bot codebase.

## 2026-03-24 - Werkzeug Dependency Vulnerability (DoS)
**Vulnerability:** Werkzeug 3.1.5 and below were vulnerable to a Denial of Service (CVE-2026-27199) due to a path traversal flaw in `safe_join` when running on Windows.
**Learning:** Even if the application code itself is secure, framework dependencies can introduce critical vulnerabilities that affect specific deployment environments (like Windows).
**Prevention:** Regularly run `pip-audit` to identify and upgrade vulnerable dependencies, even when no application-level changes are being made.
