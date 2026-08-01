"""
Weather Agent — instrumented with Contineo Observe
----------------------------------------------------
Runs the LangGraph weather agent and prints the full execution
timeline (waterfall) at the end using Contineo's TimelineService.

Usage:
    cd examples/LangGraph
    pip install -e "../../[langgraph]"
    cp .env.example .env          # add your OPENROUTER_API_KEY
    python run_with_contineo.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

# Make sure the local contineo src is importable when running from the
# examples directory without a full install.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from contineo.bus import EventBus, FeatureFlags
from contineo.events.session import SessionFinishedEvent, SessionStartedEvent
from contineo.events.base import Framework
from contineo.integrations.langgraph import ContineoCallbackHandler
from contineo.timeline import SpanStatus, TimelineService

load_dotenv()


# ---------------------------------------------------------------------------
# Waterfall printer
# ---------------------------------------------------------------------------

# ANSI colours
_RESET  = "\033[0m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_GREEN  = "\033[32m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_CYAN   = "\033[36m"
_BLUE   = "\033[34m"
_MAGENTA = "\033[35m"

_KIND_COLOUR = {
    "session":  _BOLD + _BLUE,
    "llm":      _CYAN,
    "tool":     _MAGENTA,
    "tts":      _YELLOW,
    "stt":      _YELLOW,
    "memory":   _DIM,
    "context":  _DIM,
    "error":    _RED,
    "unknown":  _DIM,
}

_KIND_ICON = {
    "session": "◉",
    "llm":     "◆",
    "tool":    "▶",
    "tts":     "♪",
    "stt":     "♫",
    "memory":  "⊕",
    "context": "⊞",
    "error":   "✖",
    "unknown": "·",
}

_STATUS_COLOUR = {
    "completed":   _GREEN,
    "failed":      _RED,
    "in_progress": _YELLOW,
}


def _bar(duration_ms: float | None, max_ms: float, width: int = 30) -> str:
    if duration_ms is None or max_ms == 0:
        return " " * width
    filled = int(round((duration_ms / max_ms) * width))
    filled = max(1, min(filled, width))
    return "█" * filled + "░" * (width - filled)


def print_waterfall(timeline) -> None:
    entries = timeline.sorted_entries
    if not entries:
        print("  (no entries)")
        return

    # Find total span for bar scaling
    max_ms = max(
        (e.duration_ms for e in entries if e.duration_ms is not None),
        default=1.0,
    )

    print()
    print(f"  {'LABEL':<40} {'STATUS':<12} {'DURATION':>10}   {'BAR'}")
    print("  " + "─" * 90)

    for entry in entries:
        kind  = entry.kind.value
        colour = _KIND_COLOUR.get(kind, _DIM)
        icon   = _KIND_ICON.get(kind, "·")
        status_colour = _STATUS_COLOUR.get(entry.status.value, "")

        label = f"{icon} {entry.label}"
        # Indent tool / memory / context / tts / stt under their parent
        if kind in ("tool", "memory", "context", "tts", "stt"):
            label = "  " + label

        duration_str = (
            f"{entry.duration_ms:>8.1f}ms" if entry.duration_ms is not None else "        —"
        )
        status_str = entry.status.value
        bar = _bar(entry.duration_ms, max_ms)

        print(
            f"  {colour}{label:<40}{_RESET} "
            f"{status_colour}{status_str:<12}{_RESET} "
            f"{_DIM}{duration_str}{_RESET}   "
            f"{colour}{bar}{_RESET}"
        )

        # Show error message inline
        if entry.error:
            print(f"    {_RED}↳ {entry.error}{_RESET}")

    print("  " + "─" * 90)
    if timeline.total_ms:
        print(f"  {_BOLD}Total session duration: {timeline.total_ms:.1f}ms{_RESET}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    # --- Wire up Contineo ---
    bus      = EventBus()
    timeline = TimelineService(bus)

    session_id = str(uuid.uuid4())
    trace_id   = str(uuid.uuid4())
    span_id    = str(uuid.uuid4())
    project_id = "weather-demo"
    agent_name = "weather-agent"

    handler = ContineoCallbackHandler(
        bus=bus,
        project_id=project_id,
        session_id=session_id,
        agent_name=agent_name,
        trace_id=trace_id,
    )

    # --- Import and build the agent (without running it yet) ---
    import importlib.util, pathlib
    spec = importlib.util.spec_from_file_location(
        "agent",
        pathlib.Path(__file__).parent / "agent.py",
    )
    agent_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_module)
    app = agent_module.build_graph()

    # --- Questions to ask ---
    questions = [
        "What is the current weather in Tokyo?",
        "Give me a 3-day forecast for London.",
    ]

    for question in questions:
        print(f"\n{'='*60}")
        print(f"  Question: {question}")
        print(f"{'='*60}")

        # Emit session.started
        await bus.publish(SessionStartedEvent(
            project_id=project_id,
            session_id=session_id,
            trace_id=trace_id,
            span_id=span_id,
            agent_name=agent_name,
            framework=Framework.LANGGRAPH,
            input=question,
        ))

        import time
        t_start = time.monotonic()

        # Run the agent with our callback handler attached
        result = app.invoke(
            {"messages": [HumanMessage(content=question)]},
            config={"callbacks": [handler]},
        )

        duration_ms = (time.monotonic() - t_start) * 1000

        # Emit session.finished
        answer = result["messages"][-1].content
        await bus.publish(SessionFinishedEvent(
            project_id=project_id,
            session_id=session_id,
            trace_id=trace_id,
            span_id=span_id,
            agent_name=agent_name,
            framework=Framework.LANGGRAPH,
            output=answer,
            duration_ms=round(duration_ms, 2),
            success=True,
        ))

        print(f"\n  Answer: {answer}\n")

        # --- Print the timeline waterfall ---
        tl = timeline.get_timeline(session_id)
        if tl:
            print(f"  Contineo Timeline  ({len(tl.entries)} spans)")
            print_waterfall(tl)
        else:
            print("  (no timeline data — check that the adapter emitted events)")

    await bus.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
