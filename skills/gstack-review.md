---
name: gstack-review
description: |
  Pre-landing code review adapted from gstack. Analyzes diffs for structural issues:
  SQL safety, LLM trust boundaries, conditional side effects, error handling gaps,
  test isolation, and completeness. Auto-fixes obvious issues, flags subjective ones.
  Adapted from garrytan/gstack /review skill.
trigger: code review, review this, review my code, pre-landing review, check the diff
tools:
  - fs_read_file
  - fs_search_files
  - sys_terminal
category: development
source: https://github.com/garrytan/gstack
---

# gstack Review — Staff Engineer Code Review

Adapted from garrytan/gstack. Core methodology: find bugs that pass CI but break in production.

## Review Protocol

### Step 1: Get the diff

```bash
git diff
# Or for branch diff:
# git fetch origin main --quiet && git diff $(git merge-base origin/main HEAD)
```

Read the full diff before starting review. Output `git diff --stat` first for overview.

### Step 2: Systematic categories

Go through each category below. For each finding, classify as:
- **AUTO-FIX**: Obvious issue you can fix directly (typos, missing imports, formatting)
- **ASK**: Subjective — requires user approval (architecture choices, naming, scope)

#### 2.1 SQL/Database Safety
- Check for raw string concatenation in queries → SQL injection
- Check for missing WHERE clauses in DELETE/UPDATE
- Check for N+1 query patterns
- Check for missing transactions on multi-step writes

#### 2.2 Error Handling
- Check every try/catch: is the catch doing anything useful or silently swallowing?
- Check for missing error paths — every external call (API, DB, file) should handle failure
- Check for "catch Exception" that's too broad

#### 2.3 Security
- Check for hardcoded secrets, tokens, keys
- Check for path traversal (user input → file path without validation)
- Check for command injection (user input → subprocess without sanitization)
- Check for missing auth/authz checks on new endpoints

#### 2.4 Completeness
- Check: are all new public functions tested?
- Check: are error branches tested, not just happy path?
- Check: are edge cases covered (empty input, null, zero, large values)?
- Check: does the PR include test files or only source changes?

#### 2.5 Side Effects
- Check: does any function mutate global state unexpectedly?
- Check: are there hidden dependencies between seemingly independent operations?
- Check: are file writes properly scoped to workspace?

#### 2.6 Test Quality
- Check: are tests testing behavior or implementation details?
- Check: are tests isolated (no shared mutable state)?
- Check: are there timing-dependent tests (sleep, setTimeout)?
- Check: do test names describe WHAT not HOW?

### Step 3: Auto-fix

For AUTO-FIX findings, fix them directly using fs_write_file. Make atomic, minimal edits.

### Step 4: Report

Output the review as a structured report:

```
## Review Summary
- Files changed: N
- AUTO-FIX: N issues fixed
- ASK: N questions for you

### AUTO-FIX applied:
1. [file:line] description of fix

### ASK (needs your decision):
1. [file:line] description of concern
```

### Step 5: Verify auto-fixes

After applying fixes, re-read the changed files to verify correctness. If any fix causes a new issue, revert it and escalate to ASK.
