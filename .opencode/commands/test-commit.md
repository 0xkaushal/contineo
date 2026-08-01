---
description: Test the latest commit and log findings to FINDINGS.md
---

A new commit has just been made to this repository. Your job is to test the SDK like a human tester would — run the code, poke at it, try to break it.

## Steps

1. Get the latest commit hash and message:
   ```
   git log -1 --pretty=format:"%H %s"
   ```

2. Identify what changed in this commit:
   ```
   git diff HEAD~1 HEAD --name-only
   git diff HEAD~1 HEAD
   ```

3. Run the existing test suite:
   ```
   uv run pytest tests/ -v
   ```

4. Based on what changed, manually test the affected code by running Python scripts. Focus on:
   - The primary user flow: `examples/LangGraph/agent_with_contineo.py` is how users are expected to use the SDK — test that it works end to end if possible
   - Any new or modified public API
   - Edge cases and error paths relevant to the change
   - Run things like a human would — try normal usage, wrong usage, boundary conditions

5. Update `FINDINGS.md` in the repo root:
   - If you found bugs or issues: append a new entry with commit hash, timestamp, issue description, steps to reproduce, and a suggested fix
   - If everything works fine: append a single log line confirming the commit hash, what was tested, and that it passed

## FINDINGS.md format

For a bug found:
```
## [COMMIT_HASH_SHORT] YYYY-MM-DD HH:MM UTC — ❌ Issue Found

**Commit:** `full_hash`
**Message:** commit message here

### Issue
Clear description of what is broken.

### Steps to Reproduce
1. Step one
2. Step two
3. Observed: X  Expected: Y

### Suggested Fix
Concrete suggestion pointing to the file and line.

---
```

For a clean run:
```
## [COMMIT_HASH_SHORT] YYYY-MM-DD HH:MM UTC — ✅ All Good

**Commit:** `full_hash`
**Message:** commit message here
**Tested:** Brief summary of what was run and checked.

---
```

Be thorough. Do not skip manual testing. The goal is to catch regressions before the developer sees them.
