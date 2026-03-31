## 2026-03-31 - [SQL Injection in API Helpers]
**Vulnerability:** SQL injection vectors in `get_availability` (dynamic table names) and `check_rules` (dynamic `IN` clause) in `api_server.py`.
**Learning:** SQLite parameters cannot be used for identifiers like table names, requiring explicit whitelisting. Dynamic `IN` clauses are better handled by fetching all records and filtering in Python for small datasets (<100) to remain secure and satisfy Bandit B608.
**Prevention:** Use hardcoded whitelists for dynamic identifiers and avoid dynamic SQL string construction for `IN` clauses.
