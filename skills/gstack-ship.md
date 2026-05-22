---
name: gstack-ship
description: |
  Release engineer adapted from gstack. Runs tests, audits coverage, pushes, opens PR.
  Bootstraps test frameworks if the project doesn't have one.
  Adapted from garrytan/gstack /ship skill.
trigger: ship it, ship this, deploy, push to production, create pr, release
tools:
  - sys_terminal
  - fs_read_file
  - fs_search_files
  - fs_write_file
category: development
source: https://github.com/garrytan/gstack
---

# Ship — Release Engineer

Adapted from garrytan/gstack. Automates the "ready to go" checklist: test → review → push → PR.

## Ship Protocol

### Step 1: Sync and test

```bash
git fetch origin main --quiet
```

Run the project's tests:

```bash
python -m pytest tests/ -v --tb=short
```

If tests fail: stop. Report failures. Do not proceed.

### Step 2: Coverage audit

```bash
python -m pytest tests/ --cov=. --cov-report=term-missing
```

Report:
- Overall coverage %
- Files with 0% coverage (new code with no tests)
- New functions without test coverage

If coverage dropped below 80%, warn. If any new file has 0% coverage, strongly recommend adding at least smoke tests.

### Step 3: Test bootstrap (if no test framework)

If the project has NO test directory or pytest config:

1. Check if `tests/` exists: `ls tests/ 2>/dev/null`
2. Check for pytest config: `grep -r "pytest" pyproject.toml setup.cfg 2>/dev/null`
3. If neither exists:
   a. Create `tests/__init__.py` and `tests/conftest.py`
   b. Write at least ONE smoke test that imports main modules
   c. Add `[tool.pytest.ini_options]` to `pyproject.toml`
   d. Verify tests pass: `python -m pytest tests/ -v`
   e. Report: "Bootstrapped test framework with N smoke tests"

### Step 4: Last review

Before pushing, do a quick self-review:
- Any commented-out code? → remove it
- Any debug prints? → remove them
- Any TODO that should be resolved? → flag it
- Any secret/token in code? → block the ship

### Step 5: Commit and push

```bash
git add -A
git status
# Only proceed if the diff looks correct
git commit -m "descriptive message summarizing changes"
git push origin $(git branch --show-current)
```

### Step 6: Open PR (if on GitHub)

```bash
gh pr create --title "PR title" --body "PR description with changes, test results, coverage"
```

If `gh` is not installed, print the git push output and instruct to open PR manually.

### Guardrails

- Never force-push to main/master
- Never commit secrets
- Never merge without tests passing
- If anything looks wrong at any step: stop and ask
