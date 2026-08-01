"""
Contineo Observe — SDK: @observe decorator.

Wraps sync and async agent run functions to automatically:
  - emit session.started / session.finished events
  - inject the callback handler into LangGraph config
  - record duration and success/failure status
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import time
import uuid
from typing import Any, Callable, TypeVar

from contineo.events.session import SessionFinishedEvent, SessionStartedEvent
from contineo.sdk.state import state
from contineo.sdk.utils import extract_input, extract_output, fire

F = TypeVar("F", bound=Callable[..., Any])


def observe(
    agent_name: str,
    *,
    session_id: str | None = None,
) -> Callable[[F], F]:
    """Decorator that fully instruments an agent run function.

    Wraps both sync and async functions. For each call it:

    1. Generates a session ID (or uses the one you supply).
    2. Emits ``session.started`` on the Event Bus.
    3. Injects the Contineo callback handler into the ``config`` kwarg
       automatically — LangGraph picks it up without any extra code.
    4. Runs the original function.
    5. Emits ``session.finished`` with duration and success/failure status.

    Args:
        agent_name: Human-readable name shown in the timeline UI.
        session_id: Fixed session ID. Auto-generated UUID when omitted.

    Example::

        @contineo.observe(agent_name="weather-agent")
        def run(question: str) -> str:
            result = app.invoke({"messages": [HumanMessage(content=question)]})
            return result["messages"][-1].content
    """
    def decorator(fn: F) -> F:
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                state.require_init()
                sid, trace_id, span_id, handler = _setup_session(agent_name, session_id)
                kwargs = _inject_callback(fn, kwargs, handler)
                await state.bus.publish(SessionStartedEvent(
                    project_id=state.project_id,
                    session_id=sid,
                    trace_id=trace_id,
                    span_id=span_id,
                    agent_name=agent_name,
                    framework=state.framework,
                    input=extract_input(args, kwargs),
                ))
                t0 = time.monotonic()
                try:
                    result = await fn(*args, **kwargs)
                    duration_ms = (time.monotonic() - t0) * 1000
                    await state.bus.publish(SessionFinishedEvent(
                        project_id=state.project_id,
                        session_id=sid,
                        trace_id=trace_id,
                        span_id=span_id,
                        agent_name=agent_name,
                        framework=state.framework,
                        output=extract_output(result),
                        duration_ms=round(duration_ms, 2),
                        success=True,
                    ))
                    return result
                except Exception as exc:
                    duration_ms = (time.monotonic() - t0) * 1000
                    await state.bus.publish(SessionFinishedEvent(
                        project_id=state.project_id,
                        session_id=sid,
                        trace_id=trace_id,
                        span_id=span_id,
                        agent_name=agent_name,
                        framework=state.framework,
                        duration_ms=round(duration_ms, 2),
                        success=False,
                        error_message=str(exc),
                    ))
                    raise
            return async_wrapper  # type: ignore[return-value]

        else:
            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                state.require_init()
                sid, trace_id, span_id, handler = _setup_session(agent_name, session_id)
                kwargs = _inject_callback(fn, kwargs, handler)
                fire(state.bus.publish(SessionStartedEvent(
                    project_id=state.project_id,
                    session_id=sid,
                    trace_id=trace_id,
                    span_id=span_id,
                    agent_name=agent_name,
                    framework=state.framework,
                    input=extract_input(args, kwargs),
                )))
                t0 = time.monotonic()
                try:
                    result = fn(*args, **kwargs)
                    duration_ms = (time.monotonic() - t0) * 1000
                    fire(state.bus.publish(SessionFinishedEvent(
                        project_id=state.project_id,
                        session_id=sid,
                        trace_id=trace_id,
                        span_id=span_id,
                        agent_name=agent_name,
                        framework=state.framework,
                        output=extract_output(result),
                        duration_ms=round(duration_ms, 2),
                        success=True,
                    )))
                    return result
                except Exception as exc:
                    duration_ms = (time.monotonic() - t0) * 1000
                    fire(state.bus.publish(SessionFinishedEvent(
                        project_id=state.project_id,
                        session_id=sid,
                        trace_id=trace_id,
                        span_id=span_id,
                        agent_name=agent_name,
                        framework=state.framework,
                        duration_ms=round(duration_ms, 2),
                        success=False,
                        error_message=str(exc),
                    )))
                    raise
            return sync_wrapper  # type: ignore[return-value]

    return decorator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _setup_session(agent_name: str, fixed_session_id: str | None):
    """Generate IDs and create the callback handler for one session."""
    sid      = fixed_session_id or str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    span_id  = str(uuid.uuid4())

    state._last_session_id = sid

    # Late import — keeps the langgraph extra truly optional
    from contineo.integrations.langgraph.callback import ContineoCallbackHandler
    handler = ContineoCallbackHandler(
        bus=state.bus,
        project_id=state.project_id,
        session_id=sid,
        agent_name=agent_name,
        trace_id=trace_id,
        framework=state.framework,
    )
    return sid, trace_id, span_id, handler


def _inject_callback(fn: Callable, kwargs: dict, handler: Any) -> dict:
    """Append the Contineo handler to config[callbacks] without overwriting.

    Only injects ``config`` if the wrapped function actually accepts it —
    either via an explicit ``config`` parameter or via ``**kwargs``.
    This prevents a ``TypeError`` when the user's function signature is
    plain, e.g. ``def run(question: str) -> str``.

    The handler is still created and will capture LLM/tool events via
    LangChain's callback mechanism when the user passes config themselves.
    When the function doesn't accept config at all (e.g. a simple wrapper),
    the handler is a no-op for that run but session events are still emitted.
    """
    params = inspect.signature(fn).parameters
    accepts_config = "config" in params or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
    )
    if not accepts_config:
        return kwargs  # don't inject — function won't accept it

    config    = dict(kwargs.get("config") or {})
    callbacks = list(config.get("callbacks") or [])
    callbacks.append(handler)
    config["callbacks"] = callbacks
    return {**kwargs, "config": config}
