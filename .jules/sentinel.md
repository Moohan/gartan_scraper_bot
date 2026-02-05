## 2026-02-05 - [SQL Injection via Dynamic Table Names]
**Vulnerability:** SQL injection risk when using f-strings for table names in SQLite queries, as table names cannot be parameterized.
**Learning:** Even if the input seems internally controlled, using dynamic SQL without validation is a high-risk pattern that static analysis tools like Bandit will flag.
**Prevention:** Use an explicit whitelist of allowed table names to validate any dynamic string before interpolating it into a SQL statement.

## 2026-02-05 - [Strict Static Analysis and Build Compatibility]
**Vulnerability:** Static analysis tools like Sourcery may flag even safe patterns (like literal strings with formatting) as potential SQL injection.
**Learning:** To satisfy strict CI checks, it's sometimes necessary to avoid all string manipulation in SQL execution, even for literal queries. Also, `lxml` builds in Alpine require specific system dependencies and compatible Python/library versions.
**Prevention:** Use literal strings directly in `execute()` calls within conditional blocks instead of building query strings dynamically. Ensure `libxml2-dev` and `libxslt-dev` are installed and use `lxml>=5.3.0` for Python 3.13 compatibility.
