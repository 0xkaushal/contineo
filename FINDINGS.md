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

> **✅ Fixed in [`29aac155`]** 2026-08-01 15:10 UTC
> `_patch_invoke` and `_patch_ainvoke` removed from `attach_langgraph`. Only `stream` and `astream` are now patched. Verified: 1 session per `invoke()` call, 1 session per `ainvoke()` call, 3 invocations → 3 sessions, idempotency (3x attach → still 1 session), stream directly → 1 session. All correct.

---

## [29aac155] 2026-08-01 15:10 UTC — ✅ All Good

**Commit:** `29aac1551ad1514d0bc004d7ffdbf6de6ea9afd4`
**Message:** feat: simplify attach_langgraph by removing invoke/ainvoke patching and updating documentation

**Tested:**

- **Double session bug fixed** — 1 session per `invoke()` call ✅
- **3 sequential invocations** → 3 isolated sessions, all complete ✅
- **Error path** — crashing node sets session to `FAILED` with correct error message ✅
- **`ainvoke()`** — 1 session, complete, correct status ✅
- **`stream()` directly** — 1 session, complete ✅
- **Idempotency** — 3x `attach()` on same graph + 1 `invoke()` → still 1 session ✅
- **Before init** — `attach()` raises `RuntimeError` ✅
- **Unsupported type** — `attach('string')` raises `TypeError` ✅
- **Real-world example** — `examples/LangGraph/agent_with_contineo.py` ran all 3 questions, full timeline with session + LLM + tool spans per run ✅

No issues found.

---

## [5e51dcb5] 2026-08-01 18:37 UTC — ❌ Issues Found

**Commit:** `5e51dcb53bbe8ef4fa9d7109e60bb8aa2226d6f3`
**Message:** feat: implement SQLite storage backend and integrate with SDK for session persistence

### What works ✅
- `SqliteStorage` connects, creates schema, writes sessions and spans to disk
- Data survives process restart — `get_timeline(session_id)` returns correct timeline from a fresh `SqliteStorage` instance
- Span data fully round-tripped: kind, label, status, duration_ms, metadata, error all persisted correctly
- `@observe` + SQLite: sessions and spans written, total_ms accurate
- `attach()` + SQLite: sessions and spans written, total_ms accurate
- Error path: failed sessions stored with `success=0`, `is_complete=1`
- `contineo.init(storage=SqliteStorage(...))` wires storage through to `TimelineService` correctly

---

### Issue 1 — `project_id` and `agent_name` always empty in DB

#### Description

Every row in the `sessions` table has `project_id=''` and `agent_name=''` regardless of what was passed to `contineo.init()` or `@contineo.observe()`. This breaks `list_sessions(project_id=...)` — it always returns `[]`.

#### Steps to Reproduce

```python
import contineo, time
from contineo.storage.sqlite import SqliteStorage

storage = SqliteStorage("/tmp/test.db")
contineo.init(project_id="weather-app", storage=storage)

@contineo.observe(agent_name="weather-agent")
def run(q: str, **kwargs): return "done"

run("hello")
time.sleep(0.3)

import sqlite3
row = sqlite3.connect("/tmp/test.db").execute("SELECT project_id, agent_name FROM sessions").fetchone()
print(row)  # ('', '')  — expected ('weather-app', 'weather-agent')
```

**Observed:** `project_id=''`, `agent_name=''`
**Expected:** `project_id='weather-app'`, `agent_name='weather-agent'`

#### Root Cause

`save_session()` calls `_project_id_from(timeline)` which reads `metadata.get("project_id", "")` from the session span. But `_on_session_started()` in `src/contineo/timeline/service.py:158` never writes `project_id` into span metadata.

#### Suggested Fix

Add `project_id` to the session span metadata in `_on_session_started()`:

```python
# src/contineo/timeline/service.py
metadata={
    "agent_name": event.agent_name,
    "framework": event.framework.value,
    "input": event.input,
    "tags": event.tags,
    "project_id": event.project_id,   # ← add this line
},
```

---

### Issue 2 — `agent_with_sqlite.py` shows no timeline and no previous sessions

#### Description

Running `examples/LangGraph/agent_with_sqlite.py` produces correct answers but the timeline is never printed and previous sessions never appear even after multiple runs. Two root causes:

1. **Issue 1 above** — `project_id` is empty so `list_sessions("weather-app")` returns nothing
2. **Race condition** — `time.sleep(0.05)` in `main()` is too short when using `attach()`. `session.finished` is emitted via `fire()` (non-blocking) inside the stream generator, so by the time `get_timeline()` is called, the session span may not yet be committed

#### Steps to Reproduce

```bash
cd examples/LangGraph
python agent_with_sqlite.py   # run twice
# Second run still shows "(no previous sessions found)" and no timeline
```

#### Suggested Fix

1. Fix Issue 1 first (adds `project_id` to metadata)
2. Increase sleep in `main()` from `0.05` to `0.2` seconds:

```python
import time; time.sleep(0.2)   # was 0.05 — too short for fire() to settle
```

---

## [c8e4fff5] 2026-08-01 18:50 UTC — ❌ Issue Found

**Commit:** `c8e4fff5ad8c37b0f0ae207fc957d4211fd19757`
**Message:** feat: enhance SQLite storage backend to include tags and project_id in session updates

### What works ✅
- Issue 1 fixed — `project_id='weather-app'` and `agent_name='weather-agent'` now correctly saved to DB ✅
- `list_sessions(project_id="weather-app")` now returns correct sessions ✅
- `list_sessions` with wrong project_id returns `[]` ✅
- `total_ms` saves accurately with both `@observe` and `attach()` ✅
- Span data fully persists and reloads correctly ✅

---

### Issue 3 — `agent_with_sqlite.py` timeline and DB writes still broken due to `time.sleep` in async context

#### Description

`agent_with_sqlite.py` still shows no timeline output and writes nothing to the DB. The `time.sleep(0.2)` fix (replacing the original 0.05s) does not solve the problem because **`main()` is an async function run under `asyncio.run()`**. Calling `time.sleep()` inside an async context blocks the entire event loop, preventing `fire()` tasks from executing. This means:
- `session.started` / `session.finished` events are never published
- The in-memory timeline is never populated
- Nothing is written to SQLite

#### Steps to Reproduce

```bash
cd examples/LangGraph
python agent_with_sqlite.py
# No timeline shown, DB has 0 sessions and 0 spans
```

Confirm DB is empty:
```python
import sqlite3
conn = sqlite3.connect("examples/LangGraph/contineo.db")
print(conn.execute("SELECT COUNT(*) FROM sessions").fetchone())  # (0,)
```

**Observed:** 0 sessions in DB, no timeline printed.
**Expected:** Sessions written to DB, timeline printed per run.

#### Root Cause

`fire()` in `src/contineo/sdk/utils.py` uses `loop.create_task(coro)` when a loop is running. But `time.sleep()` is a blocking call — it suspends the Python thread without yielding to the event loop, so scheduled tasks never get a chance to run during that sleep window.

#### Suggested Fix

Replace `time.sleep(0.2)` with `await asyncio.sleep(0.2)` in `agent_with_sqlite.py`:

```python
# examples/LangGraph/agent_with_sqlite.py — inside main()
import asyncio
await asyncio.sleep(0.2)   # yields to event loop so fire() tasks can execute
```

This is the correct pattern inside any `async def` function. `time.sleep` should never be used inside async code.

---
