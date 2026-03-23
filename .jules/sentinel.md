# Sentinel Security Journal

## 2026-03-23 - Dynamic SQL Construction and CI Security Scanners
**Vulnerability:** Potential SQL Injection (Bandit B608, Sourcery `avoid-sql-string-concatenation`).
**Learning:** Even safe SQL patterns (e.g., parameterizing values while dynamically generating placeholders for an `IN` clause) are blocked by strict CI security scanners. While suppression comments can handle Bandit, some scanners like Sourcery may remain persistent or require project-level configuration to ignore.
**Prevention:** For small datasets (like a single fire station's crew), refactoring to fetch all records and filter in Python satisfies all scanners while maintaining safety and performance. This avoids the "arms race" with static analysis tools and ensures a blocking-free CI pipeline.
