---
name: gstack-cso
description: |
  Chief Security Officer audit adapted from gstack. OWASP Top 10 + STRIDE threat model.
  Zero-noise approach: 17 false positive exclusions, 8/10+ confidence gate,
  independent finding verification. Each finding includes concrete exploit scenario.
  Adapted from garrytan/gstack /cso skill.
trigger: security audit, security review, cso, owasp, stride, check security, vulnerability scan
tools:
  - fs_read_file
  - fs_search_files
  - fs_write_file
  - sys_terminal
category: security
source: https://github.com/garrytan/gstack
---

# Chief Security Officer — OWASP + STRIDE Audit

Adapted from garrytan/gstack. Core promise: zero-noise findings with concrete exploit scenarios.

## Audit Protocol

### Step 1: Scope detection

```bash
git diff --stat HEAD~1  # recent changes
# Or: git diff --name-only origin/main..HEAD
```

Focus on changed files. Don't audit unchanged code unless it's directly adjacent to changes.

### Step 2: OWASP Top 10 Scan

For each changed file, check:

| # | Vulnerability | What to look for |
|---|--------------|------------------|
| A01 | Broken Access Control | New routes/endpoints without auth checks |
| A02 | Cryptographic Failures | Hardcoded keys, weak algorithms (MD5/SHA1), plaintext secrets |
| A03 | Injection | SQL concatenation, shell command from user input, unsanitized eval() |
| A04 | Insecure Design | Missing rate limiting, user-controlled file paths |
| A05 | Security Misconfiguration | Debug mode enabled, verbose errors, default credentials |
| A06 | Vulnerable Components | Outdated dependencies (check requirements.txt/pyproject.toml) |
| A07 | Auth Failures | Weak password policies, missing session timeout, no MFA |
| A08 | Software & Data Integrity | Unsigned updates, unverified deserialization (pickle, yaml.load) |
| A09 | Logging & Monitoring | No audit log for sensitive operations, missing error logging |
| A10 | SSRF | fetch/curl with user-supplied URL, internal host access |

### Step 3: STRIDE Threat Model

1. **Spoofing**: Can an attacker impersonate a user/service?
2. **Tampering**: Can data be modified in transit or at rest?
3. **Repudiation**: Can malicious actions be denied? (Missing audit trail?)
4. **Information Disclosure**: Are errors leaking stack traces? Secrets in logs?
5. **Denial of Service**: Can a single request exhaust resources?
6. **Elevation of Privilege**: Can a lower-privilege user gain higher access?

### Step 4: Finding verification

For each potential finding:

1. **Write a concrete exploit scenario**: "An attacker could X by Y, resulting in Z"
2. **Rate confidence 1-10**: Only include findings rated 8+ (high confidence)
3. **Verify independently**: Can the finding be confirmed without assuming the worst?
4. **False positive exclusion**: Skip if matching any of:
   - Test-only code (test fixtures, mock data)
   - Already behind auth that's verified elsewhere
   - Input already validated at a higher layer
   - Acceptable risk for the use case (documented trade-off)

### Step 5: Report

Output structured report:

```
## CSO Security Audit

**Scope:** N files changed
**Findings:** N (X CRITICAL, Y HIGH, Z MEDIUM)

### CRITICAL
1. [file:line] Category: description
   Exploit: concrete exploit scenario
   Fix: specific remediation

### HIGH
...

### MEDIUM
...

### Verified Safe
- List things checked that are properly handled
```

For each finding that can be auto-fixed without risk, apply the fix and note it. For fixes that require architectural decisions, flag as ASK.
