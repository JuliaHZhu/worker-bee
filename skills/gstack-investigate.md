---
name: gstack-investigate
description: |
  Systematic root-cause debugging adapted from gstack. Iron Law: no fixes without investigation.
  Traces data flow, tests hypotheses, stops after 3 failed fixes.
  Adapted from garrytan/gstack /investigate skill.
trigger: investigate, debug, root cause, why is this happening, trace this bug, debugging, what caused
tools:
  - fs_read_file
  - fs_search_files
  - sys_terminal
  - browse_navigate
  - browse_snapshot
  - browse_js
category: development
source: https://github.com/garrytan/gstack
---

# Systematic Investigation — Root Cause Debugging

Adapted from garrytan/gstack. Iron Law: **No fixes without investigation.** If you don't understand why it broke, your fix is a guess.

## The Iron Law

> If you can't explain the root cause, your fix is a guess.
> Stop after 3 failed fixes — switch to investigation mode.

## Investigation Protocol

### Step 1: Reproduce

Before touching any code:

1. Reproduce the bug. Run the failing test, trigger the error, or replay the exact steps.
2. If you can't reproduce it, document exact steps tried. The bug may be environmental.
3. Capture the error message, stack trace, and relevant state at failure point.

### Step 2: Trace the data flow

For the failing operation, trace backwards from the error:

```
Error point (where it crashes/wrong output)
    ↑
What produced this value?
    ↑
What input led to this state?
    ↑
Where did that input come from?
    ↑
Root cause (the actual mistake)
```

Use `fs_read_file` to read the code at each step. Use `fs_search_files` to find callers/setters.

### Step 3: Form a hypothesis

Before making any change, write down:

```
HYPOTHESIS: The bug is caused by [X] because [Y].
PREDICTION: If I [change/verify Z], the behavior should [expected result].
```

### Step 4: Test the hypothesis

- Add a temporary print/debug statement at the suspected point
- Run the reproduction steps
- Does the output match your prediction?

If YES → you understand the root cause. Proceed to fix.
If NO → your hypothesis is wrong. Form a new one. Don't fix blind.

### Step 5: Fix (only after confirmed hypothesis)

1. Make the minimal fix that addresses the root cause
2. Run the reproduction test — does it pass now?
3. Check: could this fix break anything else? Search for callers/consumers.
4. Add a regression test that would have caught this bug

### Step 6: Stop rule

After 3 failed fix attempts:
- Stop. Don't try a 4th fix.
- Restate what you've learned.
- Ask the user: "I've tried 3 approaches. Here's what I know and what I'm uncertain about. How would you like to proceed?"

## Investigation Techniques

### Binary search on commits

```bash
git log --oneline -20
git diff <commit>~1..<commit> -- path/to/failing/file
```

### State inspection

For runtime bugs, add strategic fs_write_file debug outputs:

```
# Read the current state at critical points
# Before: fs_read_file on the file in question
# After: fs_write_file a debug log
```

### Browser inspection (for web bugs)

```
browse_navigate to the failing page
browse_snapshot to see current state
browse_js to inspect runtime values: "document.querySelector('.error').textContent"
```

### Isolation

Can you reproduce with minimal inputs? Strip away:
- External dependencies → mock them
- Complex inputs → simplify to minimal case
- Concurrent operations → serialize them

If the bug disappears during isolation, the cause was one of the removed factors.
