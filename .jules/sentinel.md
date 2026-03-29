# Sentinel Journal

## 2026-03-29 - Sourcery SQL Injection Blocker
**Vulnerability:** Sourcery flagged the use of dynamic SQL placeholders (`?,?,\?`) as a potential SQL injection risk, even though it was safe via parameterization.
**Learning:** Some CI security scanners have strict rules against any form of SQL string concatenation or dynamic placeholder generation.
**Prevention:** For small datasets, prefer fetching all records and filtering in Python, or use a proper ORM/Query Builder that the scanner recognizes as safe.
