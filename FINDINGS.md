# Contineo SDK — Test Findings

Every commit is tested manually and logged here.

---

## [4147262d] 2026-08-01 13:51 UTC — ❌ Issue Found

**Commit:** `4147262d9552e6a28c8a5d5e28450699b35034cc`
**Message:** feat: implement Contineo Observe SDK with initialization, observation, and timeline accessors

### Issue

The `@contineo.observe` decorator crashes any agent function that does not explicitly accept a `config` keyword argument. The decorator unconditionally injects `config` into the function's `kwargs` before calling it, but the user-facing example `run(question: str)` has no `config` parameter.

This means the primary intended usage pattern — the exact 3-line integration shown in `examples/LangGraph/agent_with_contineo.py` — fails immediately.

### Steps to Reproduce

```python
import contineo

contineo.init(project_id="weather-app")

@contineo.observe(agent_name="weather-agent")
def run(question: str) -> str:
    return "hello"

run("What is the weather?")
```

**Observed:**
```
TypeError: run() got an unexpected keyword argument 'config'
```

**Expected:** Function runs normally, session is recorded on the timeline.

Also reproduced by running the example directly:
```
uv run python examples/LangGraph/agent_with_contineo.py
```

Affects both sync (`sync_wrapper` line 117) and async (`async_wrapper` line 70) paths in `src/contineo/sdk/decorator.py`.

### Test Suite

109/109 unit tests pass — the bug is not covered by any existing test.

### Suggested Fix

In `src/contineo/sdk/decorator.py`, the `_inject_callback` function should only pass `config` through to the wrapped function if the function's signature actually accepts it (either a `config` parameter or `**kwargs`).

```python
import inspect

def _inject_callback(fn: Callable, kwargs: dict, handler: Any) -> dict:
    """Append the Contineo handler to config[callbacks] without overwriting.
    Only injects config if the wrapped function accepts it."""
    sig = inspect.signature(fn)
    params = sig.parameters
    accepts_config = "config" in params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
    if not accepts_config:
        return kwargs  # don't inject — function won't accept it

    config = dict(kwargs.get("config") or {})
    callbacks = list(config.get("callbacks") or [])
    callbacks.append(handler)
    config["callbacks"] = callbacks
    return {**kwargs, "config": config}
```

Update call sites in both `sync_wrapper` and `async_wrapper` to pass `fn` as the first argument:
```python
kwargs = _inject_callback(fn, kwargs, handler)
```

---

## [d23cef93] 2026-08-01 14:00 UTC — ✅ All Good

**Commit:** `d23cef93dbca2b11799b1ff83243cb77684f7c82`
**Message:** feat: add manual testing instructions and findings logging for SDK commits
**Tested:** Checked what changed (`.opencode/commands/test-commit.md` added, `FINDINGS.md` created — no SDK source code modified). Ran full test suite: 109/109 passed. Ran `uv run python examples/LangGraph/agent_with_contineo.py` — confirms the pre-existing `[4147262d]` decorator bug is still present (unchanged by this commit, which touched no SDK code). No regressions introduced.

---
