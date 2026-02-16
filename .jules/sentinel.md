## 2026-02-16 - SQL Injection via Dynamic Table Names
**Vulnerability:** Use of f-strings to interpolate table and column names into SQLite queries.
**Learning:** Even when table names are internally controlled, dynamic SQL construction is flagged by security scanners and presents a risk if the control flow ever changes. Whitelisting allowed table names and using static SQL strings is the most secure pattern.
**Prevention:** Always use parameterized queries for values and a strict whitelist for dynamic table or column names.

## 2026-02-16 - Credential Reflection in Logs
**Vulnerability:** Logging raw response content (`login_resp.text`) on authentication failure and printing usernames to stdout.
**Learning:** Authentication responses may reflect submitted credentials or reveal system internals that could be useful to an attacker. Debug prints in production code can easily leak sensitive data.
**Prevention:** Redact response content in error logs for authentication endpoints and use proper logging levels that exclude sensitive data from production output.

## 2026-02-16 - CI/CD Security Scanner Maintenance
**Vulnerability:** Use of `safety` version 3.x in non-interactive CI environments without an account/login.
**Learning:** Some security tools (like `safety`) may introduce breaking changes or authentication requirements in newer versions that can block CI pipelines.
**Prevention:** Prefer tools with stable, non-interactive CLI interfaces for CI (like `pip-audit`) and keep workflow dependencies pinned or regularly reviewed for such changes.

## 2026-02-16 - System Dependencies for Secure Parsing
**Vulnerability:** Build failure when installing `lxml` on Alpine-based Docker images due to missing `libxml2` and `libxslt` development packages.
**Learning:** Using more robust and potentially more secure parsers (like `lxml` via `BeautifulSoup`) often requires system-level development libraries during the build phase.
**Prevention:** Ensure that Dockerfiles include necessary `.build-deps` for Python packages that compile C extensions, and include corresponding runtime libraries in the final stage.
