# Sentinel Security Journal

## 2026-03-23 - Parameterized 'IN' Clause Optimization
**Vulnerability:** Potential SQL Injection (Bandit B608) flagged due to f-string interpolation for dynamic `IN` clause placeholders.
**Learning:** While the original code was safe because it only interpolated placeholders (`?`), automated scanners often flag any f-string SQL. Refactoring to fetch the entire table for Python-side filtering (to satisfy the scanner) introduced significant performance regressions and schema compatibility issues (e.g., column count mismatch for positional unpacking).
**Prevention:** Use `# nosec B608` for safe interpolation of placeholders when the number of parameters is dynamic, as this preserves database-level optimization (indexes) and prevents runtime logic breakages while clearly documenting the security consideration.
