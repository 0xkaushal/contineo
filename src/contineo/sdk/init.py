"""
Contineo Observe — SDK: init().

Initialises the global bus, timeline, and framework detection.
Call once at application startup.
"""

from __future__ import annotations

import importlib.util

from contineo.bus.event_bus import EventBus
from contineo.bus.flags import FeatureFlags
from contineo.events.base import Framework
from contineo.sdk.state import state
from contineo.timeline.service import TimelineService


def _detect_framework() -> Framework:
    """Inspect installed packages and return the best matching framework."""
    checks = [
        ("langgraph", Framework.LANGGRAPH),
        ("pipecat",   Framework.PIPECAT),
        ("livekit",   Framework.LIVEKIT),
        ("openai",    Framework.OPENAI),
    ]
    for package, framework in checks:
        if importlib.util.find_spec(package) is not None:
            return framework
    return Framework.UNKNOWN


def init(
    project_id: str,
    *,
    framework: Framework | None = None,
    flags: FeatureFlags | None = None,
) -> None:
    """Initialise Contineo Observe.

    Call this once at application startup — before any agent runs.

    Args:
        project_id: Identifies your project. Used on every emitted event.
        framework:  The agent framework in use. Auto-detected when omitted.
        flags:      Feature flags. Reads from environment variables when omitted.

    Example::

        import contineo
        contineo.init(project_id="my-weather-app")
    """
    state.project_id  = project_id
    state.flags       = flags or FeatureFlags.load()
    state.framework   = framework or _detect_framework()
    state.bus         = EventBus(flags=state.flags)
    state.timeline    = TimelineService(state.bus, flags=state.flags)
    state.initialised = True
