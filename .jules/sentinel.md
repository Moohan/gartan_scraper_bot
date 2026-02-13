## 2026-02-13 - SQL Injection and Sensitive Logging Hardening
**Vulnerability:** Potential SQL injection in `get_availability` due to dynamic table name interpolation and sensitive credential logging in `gartan_fetch.py`.
**Learning:** Even when internal logic seems safe, dynamic SQL construction with f-strings triggers static analysis alerts and creates future risks. Whitelisting and static SQL are safer.
**Prevention:** Use whitelists for dynamic table/column names and strictly avoid logging raw credentials or session identifiers in debug prints.
