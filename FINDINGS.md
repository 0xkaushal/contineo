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

> **✅ Fixed in [`f463dc09`]** 2026-08-01 14:00 UTC
> Verified: `TypeError: run() got an unexpected keyword argument 'config'` no longer reproduces. `_inject_callback` now checks the function signature via `inspect` before injecting `config`. `examples/LangGraph/agent_with_contineo.py` runs end to end successfully.
>
> ⚠️ **Partial fix note:** LLM and tool spans are not recorded when the user's function does not accept `config` (e.g. `def run(question: str)`), because the callback handler is not injected in that case. Only the session span is tracked. This is a silent limitation — see new issue below.

---

## [af57d57] 2026-08-01 — ✅ All Good

**Commit:** `af57d57396fad7b5fa0d868f747e819d633a9283`
**Message:** docs: update findings log with recent test results and confirm no SDK changes
**Tested:** Confirmed only `FINDINGS.md` changed (no SDK source modified). Ran full test suite: 109/109 passed. Re-ran open bug reproduction for `[4147262d]` — bug still reproduces (unchanged, as expected; this commit touched no SDK code). Ran `uv run python examples/LangGraph/agent_with_contineo.py` — pre-existing decorator crash persists. No regressions introduced by this commit.

---

## [d23cef93] 2026-08-01 14:00 UTC — ✅ All Good

**Commit:** `d23cef93dbca2b11799b1ff83243cb77684f7c82`
**Message:** feat: add manual testing instructions and findings logging for SDK commits
**Tested:** Checked what changed (`.opencode/commands/test-commit.md` added, `FINDINGS.md` created — no SDK source code modified). Ran full test suite: 109/109 passed. Ran `uv run python examples/LangGraph/agent_with_contineo.py` — confirms the pre-existing `[4147262d]` decorator bug is still present (unchanged by this commit, which touched no SDK code). No regressions introduced.

---

## [f463dc09] 2026-08-01 14:10 UTC — ❌ Issue Found

**Commit:** `f463dc0925c504f3ded8d0b1d6f913619a037cc9`
**Message:** feat: enhance @observe decorator to prevent TypeError for functions without config parameter and add comprehensive tests

### Issue

The `TypeError` crash is fixed, but when the user's function does not accept `config` (e.g. `def run(question: str) -> str` as shown in `examples/LangGraph/agent_with_contineo.py`), the callback handler is silently not injected. This means **LLM spans and tool spans are never recorded** — only the top-level session span appears on the timeline.

### Steps to Reproduce

```bash
uv run python examples/LangGraph/agent_with_contineo.py
```

Observe the timeline output — only 1 span per session (session only). Expected: session + LLM + tool spans.

Or directly:

```python
import contineo
contineo.init(project_id="test")

@contineo.observe(agent_name="weather-agent")
def run(question: str) -> str:
    return "sunny"

run("Tokyo")
import time; time.sleep(0.1)
tl = contineo.get_timeline(contineo.last_session_id())
print(len(tl.entries))  # prints 1, LLM/tool spans missing
```

**Observed:** `Timeline — 1 spans` per run.
**Expected:** Session + LLM + tool spans all recorded.

### Suggested Fix

Update `examples/LangGraph/agent_with_contineo.py` to pass `config` through so LangGraph receives the callbacks:

```python
@contineo.observe(agent_name="weather-agent")
def run(question: str, **kwargs) -> str:
    result = app.invoke(
        {"messages": [HumanMessage(content=question)]},
        config=kwargs.get("config"),
    )
    return result["messages"][-1].content
```

And update the docs/README to show that the wrapped function must forward `config` to `app.invoke`.

### Test Suite

118/118 pass.

> **✅ Fixed in [`f463dc09`]** 2026-08-01 14:20 UTC
> Verified: `examples/LangGraph/agent_with_contineo.py` was updated in the same commit to use `def run(question: str, **kwargs)` and forward `config=kwargs.get("config")` to `app.invoke`. Timeline now shows full spans — session + LLM + tool calls. Confirmed with 3 questions, 4-5 spans each.

---

## Manual Test Run — 2026-08-01 14:20 UTC — ✅ All Good

**Commit:** `f463dc0925c504f3ded8d0b1d6f913619a037cc9` (no new commit — manual run)
**Tested:**
- 121/121 unit tests pass
- `examples/LangGraph/agent_with_contineo.py` runs end to end — all 3 questions answered, full timeline with session + LLM + tool spans
- `@observe` raises `RuntimeError` before `init()` ✅
- Failed agent sets session status to `FAILED` with correct error message ✅
- Async `@observe` works correctly ✅
- Fixed `session_id` is honoured ✅
- Multiple sessions are isolated ✅
- `CONTINEO_ENABLE_TIMELINE=false` suppresses timeline ✅

No issues found.

---

## Manual Test Run — 2026-08-01 14:40 UTC — ❌ Issue Found

**Commit:** `f463dc0925c504f3ded8d0b1d6f913619a037cc9` (unstaged: `contineo.attach()`)
**New files tested:** `src/contineo/sdk/attach.py`, `src/contineo/integrations/langgraph/patch.py`

### What works ✅
- 139/139 unit tests pass
- Framework detection correctly identifies LangGraph compiled graph
- `attach()` raises `RuntimeError` if called before `init()`
- `attach()` raises `TypeError` for unsupported object types with a clear message
- `invoke()` records session span, marks complete on success, FAILED on error
- `ainvoke()` works correctly — session recorded, is_complete, status correct
- Idempotency flag (`_contineo_patched`) prevents double-wrapping on second `attach()` call

---

### Issue — Double session created per `invoke()` call

#### Description

Every single call to `app.invoke()` creates **2 sessions** on the timeline instead of 1. This is because LangGraph's own `invoke` implementation internally calls `self.stream()` — and since both `invoke` and `stream` are independently patched by `attach_langgraph`, `_setup()` (which creates a new session) fires twice per user-facing call.

#### Steps to Reproduce

```python
import contineo, time
from langgraph.graph import StateGraph, START, END

# ... build any graph ...
app = g.compile()

contineo.init(project_id="test")
contineo.attach(app, agent_name="test-agent")

app.invoke({"messages": [...]})   # one user call
time.sleep(0.1)

from contineo.sdk.state import state
print(len(state.timeline.session_ids))  # prints 2, expected 1
```

**Observed:** 2 sessions per `invoke()` call.
**Expected:** 1 session per `invoke()` call.

#### Root Cause

In `src/contineo/integrations/langgraph/patch.py`, `_patch_invoke` and `_patch_stream` are patched independently. LangGraph's `Pregel.invoke` calls `self.stream()` internally (`langgraph/pregel/main.py`), so the patched `stream` fires a second `_setup()` from within the first patched `invoke`.

#### Suggested Fix

Only patch `stream` and `astream`. Do not patch `invoke` and `ainvoke` separately — let LangGraph's native routing handle them. Since `invoke` always routes through `stream` internally, patching `stream` alone is sufficient to capture every run:

```python
def attach_langgraph(graph: Any, agent_name: str) -> None:
    if getattr(graph, _CONTINEO_PATCHED, False):
        return
    _patch_stream(graph, agent_name)
    _patch_astream(graph, agent_name)
    setattr(graph, _CONTINEO_PATCHED, True)
```

If direct `invoke`/`ainvoke` patching is desired for other reasons, add a guard inside each patch to check whether a session is already in-progress for this call chain before calling `_setup()`.

---
