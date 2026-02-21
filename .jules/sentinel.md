## 2026-02-21 - [CI Fixes: lxml building and safety scan requirements]
**Vulnerability:** Surprising build gap in Docker architecture and CI dependency scanning failure.
**Learning:** Alpine-based Python images lack development headers by default. Building `lxml` from source requires `libxml2-dev` and `libxslt-dev`. Also, `safety` version 3.x is not suitable for non-interactive CI environments as it requires registration/login.
**Prevention:** Include necessary system libraries for C-extensions in Docker build stages and runtime. Prefer `pip-audit` for headless dependency scanning in CI/CD pipelines.
