"""
Contineo Observe — SDK: attach().

Attaches Contineo to a framework object (graph, chain, pipeline, etc.)
by patching its invoke/run methods in-place.

The user writes zero Contineo-specific code inside their agent:

    app = build_graph()
    contineo.attach(app, agent_name="weather-agent")

    # Completely unchanged — no kwargs, no config forwarding
    result = app.invoke({"messages": [HumanMessage(content=question)]})

attach() detects the type of object passed and routes to the correct
framework adapter. New frameworks are added here as new elif branches
without touching any existing code.
"""

from __future__ import annotations

from typing import Any

from contineo.sdk.state import state


def attach(obj: Any, agent_name: str) -> None:
    """Attach Contineo Observe to a framework object.

    Patches the object's invoke/run/stream methods in-place so every
    execution is automatically observed — no changes to user code needed.

    Currently supported objects:
        - LangGraph compiled graph  (CompiledStateGraph / Pregel)
        - LangChain Runnable        (chains, prompts, etc.)

    Args:
        obj:        The framework object to observe.
        agent_name: Human-readable name shown in the timeline.

    Raises:
        RuntimeError: If contineo.init() has not been called yet.
        TypeError:    If the object type is not recognised.

    Example::

        import contineo

        contineo.init(project_id="weather-app")

        app = build_graph()
        contineo.attach(app, agent_name="weather-agent")

        # No other changes — invoke exactly as before
        result = app.invoke({"messages": [HumanMessage(content=question)]})
    """
    state.require_init()

    framework = _detect_object_framework(obj)

    if framework == "langgraph":
        from contineo.integrations.langgraph.patch import attach_langgraph
        attach_langgraph(obj, agent_name)

    elif framework == "langchain":
        # LangChain Runnables share the same LangGraph callback mechanism
        from contineo.integrations.langgraph.patch import attach_langgraph
        attach_langgraph(obj, agent_name)

    else:
        raise TypeError(
            f"contineo.attach() does not recognise object of type "
            f"'{type(obj).__name__}'. "
            f"Supported: LangGraph compiled graph, LangChain Runnable. "
            f"For other frameworks, emit events manually via the Event Bus."
        )


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------

def _detect_object_framework(obj: Any) -> str | None:
    """Inspect the object's class hierarchy to determine its framework."""
    mro = [cls.__name__ for cls in type(obj).__mro__]
    qualname = f"{type(obj).__module__}.{type(obj).__name__}"

    # LangGraph compiled graph — check most specific first
    if any(name in mro for name in ("CompiledStateGraph", "Pregel", "CompiledGraph")):
        return "langgraph"

    # LangChain Runnable (chains, prompts, retrievers, etc.)
    if "Runnable" in mro or "langchain" in qualname:
        return "langchain"

    return None
