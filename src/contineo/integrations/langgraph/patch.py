"""
Contineo Observe — LangGraph attach() patcher.

Patches a compiled LangGraph graph object in-place so that every call to
invoke / ainvoke / stream / astream is automatically observed by Contineo.

The user writes zero Contineo-specific code inside their agent.
They just call contineo.attach(app) once after compiling the graph.

Implementation note:
    Only stream and astream are patched — NOT invoke/ainvoke.
    LangGraph's Pregel.invoke internally calls self.stream(), so patching
    both would create 2 sessions per user-facing invoke() call.
    Patching stream/astream alone is sufficient to capture every execution
    path including direct invoke() calls.

Usage::

    app = build_graph()
    contineo.attach(app, agent_name="weather-agent")

    # Completely unchanged from a plain agent — no kwargs, no config forwarding
    result = app.invoke({"messages": [HumanMessage(content=question)]})
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Iterator, AsyncIterator

from contineo.events.base import Framework
from contineo.events.session import SessionFinishedEvent, SessionStartedEvent
from contineo.sdk.state import state
from contineo.sdk.utils import extract_output, fire


# Sentinel attribute set on patched graphs so attach() is idempotent
_CONTINEO_PATCHED = "_contineo_patched"


def attach_langgraph(graph: Any, agent_name: str) -> None:
    """Patch a compiled LangGraph graph to emit Contineo events on every run.

    Only patches stream and astream — invoke/ainvoke route through these
    internally, so patching them directly would double-fire session creation.

    The patch is idempotent — calling attach() on an already-patched graph
    is a no-op.

    Args:
        graph:      A compiled LangGraph graph (CompiledStateGraph / Pregel).
        agent_name: Human-readable name shown in the timeline.
    """
    if getattr(graph, _CONTINEO_PATCHED, False):
        return  # already patched — nothing to do

    _patch_stream(graph, agent_name)
    _patch_astream(graph, agent_name)

    setattr(graph, _CONTINEO_PATCHED, True)


# ---------------------------------------------------------------------------
# sync stream
# ---------------------------------------------------------------------------
def _patch_stream(graph: Any, agent_name: str) -> None:
    original = graph.stream

    def patched_stream(input: Any, config: dict | None = None, **kwargs: Any) -> Iterator:
        sid, trace_id, span_id, handler = _setup(agent_name)
        config = _inject(config, handler)

        fire(state.bus.publish(SessionStartedEvent(
            project_id=state.project_id,
            session_id=sid,
            trace_id=trace_id,
            span_id=span_id,
            agent_name=agent_name,
            framework=Framework.LANGGRAPH,
            input=_input_str(input),
        )))

        t0 = time.monotonic()
        last_chunk = None
        try:
            for chunk in original(input, config, **kwargs):
                last_chunk = chunk
                yield chunk
            duration_ms = (time.monotonic() - t0) * 1000
            fire(state.bus.publish(SessionFinishedEvent(
                project_id=state.project_id,
                session_id=sid,
                trace_id=trace_id,
                span_id=span_id,
                agent_name=agent_name,
                framework=Framework.LANGGRAPH,
                output=extract_output(last_chunk),
                duration_ms=round(duration_ms, 2),
                success=True,
            )))
        except Exception as exc:
            duration_ms = (time.monotonic() - t0) * 1000
            fire(state.bus.publish(SessionFinishedEvent(
                project_id=state.project_id,
                session_id=sid,
                trace_id=trace_id,
                span_id=span_id,
                agent_name=agent_name,
                framework=Framework.LANGGRAPH,
                duration_ms=round(duration_ms, 2),
                success=False,
                error_message=str(exc),
            )))
            raise

    graph.stream = patched_stream


# ---------------------------------------------------------------------------
# async astream
# ---------------------------------------------------------------------------

def _patch_astream(graph: Any, agent_name: str) -> None:
    original = graph.astream

    async def patched_astream(input: Any, config: dict | None = None, **kwargs: Any) -> AsyncIterator:
        sid, trace_id, span_id, handler = _setup(agent_name)
        config = _inject(config, handler)

        await state.bus.publish(SessionStartedEvent(
            project_id=state.project_id,
            session_id=sid,
            trace_id=trace_id,
            span_id=span_id,
            agent_name=agent_name,
            framework=Framework.LANGGRAPH,
            input=_input_str(input),
        ))

        t0 = time.monotonic()
        last_chunk = None
        try:
            async for chunk in original(input, config, **kwargs):
                last_chunk = chunk
                yield chunk
            duration_ms = (time.monotonic() - t0) * 1000
            await state.bus.publish(SessionFinishedEvent(
                project_id=state.project_id,
                session_id=sid,
                trace_id=trace_id,
                span_id=span_id,
                agent_name=agent_name,
                framework=Framework.LANGGRAPH,
                output=extract_output(last_chunk),
                duration_ms=round(duration_ms, 2),
                success=True,
            ))
        except Exception as exc:
            duration_ms = (time.monotonic() - t0) * 1000
            await state.bus.publish(SessionFinishedEvent(
                project_id=state.project_id,
                session_id=sid,
                trace_id=trace_id,
                span_id=span_id,
                agent_name=agent_name,
                framework=Framework.LANGGRAPH,
                duration_ms=round(duration_ms, 2),
                success=False,
                error_message=str(exc),
            ))
            raise

    graph.astream = patched_astream


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _setup(agent_name: str) -> tuple:
    """Generate IDs and create the LangGraph callback handler."""
    sid      = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    span_id  = str(uuid.uuid4())

    state._last_session_id = sid

    from contineo.integrations.langgraph.callback import ContineoCallbackHandler
    handler = ContineoCallbackHandler(
        bus=state.bus,
        project_id=state.project_id,
        session_id=sid,
        agent_name=agent_name,
        trace_id=trace_id,
        framework=Framework.LANGGRAPH,
    )
    return sid, trace_id, span_id, handler


def _inject(config: dict | None, handler: Any) -> dict:
    """Inject the Contineo handler into config[callbacks]."""
    config    = dict(config or {})
    callbacks = list(config.get("callbacks") or [])
    callbacks.append(handler)
    config["callbacks"] = callbacks
    return config


def _input_str(input: Any) -> str | None:
    """Best-effort string representation of the graph input."""
    if input is None:
        return None
    if isinstance(input, str):
        return input[:500]
    if isinstance(input, dict):
        messages = input.get("messages", [])
        if messages:
            last = messages[-1]
            content = getattr(last, "content", None) or str(last)
            return str(content)[:500]
    return str(input)[:500]
