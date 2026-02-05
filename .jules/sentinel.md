## 2026-02-05 - [SQL Injection via Dynamic Table Names]
**Vulnerability:** SQL injection risk when using f-strings for table names in SQLite queries, as table names cannot be parameterized.
**Learning:** Even if the input seems internally controlled, using dynamic SQL without validation is a high-risk pattern that static analysis tools like Bandit will flag.
**Prevention:** Use an explicit whitelist of allowed table names to validate any dynamic string before interpolating it into a SQL statement.
