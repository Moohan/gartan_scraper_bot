## 2024-05-20 - Initial Setup
**Learning:** Bolt's journal has been created. I will use this to document critical performance learnings going forward.
**Action:** Adhere to the journaling guidelines specified in the instructions.

## 2024-05-20 - Gitignore Configuration is Critical
**Learning:** A misconfigured `.gitignore` file led to a Python bytecode file (`.pyc`) being included in a commit. This is a serious anti-pattern that pollutes the repository.
**Action:** Always ensure that `.gitignore` is correctly configured to exclude generated files, build artifacts, and local environment files before committing any changes. Specifically for Python, `__pycache__/` and `*.pyc` should always be included.
