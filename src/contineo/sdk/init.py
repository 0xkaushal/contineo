"""
Contineo Observe — SDK: init().
"""

from __future__ import annotations

import importlib.util

from contineo.bus.event_bus import EventBus
from contineo.bus.flags import FeatureFlags
from contineo.events.base import Framework
from contineo.sdk.state import state
from contineo.timeline.service import TimelineService


def _detect_framework() -> Framework:
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
    storage=None,
) -> None:
    """Initialise Contineo Observe.

    Args:
        project_id: Identifies your project. Used on every emitted event.
        framework:  The agent framework in use. Auto-detected when omitted.
        flags:      Feature flags. Reads from environment variables when omitted.
        storage:    Optional StorageBackend for local persistence.
                    Defaults to in-memory only.

    Example — in-memory (default, zero setup)::

        import contineo
        contineo.init(project_id="my-app")

    Example — SQLite local persistence::

        from contineo.storage import SqliteStorage
        contineo.init(project_id="my-app", storage=SqliteStorage("./contineo.db"))
    """
    state.project_id  = project_id
    state.flags       = flags or FeatureFlags.load()
    state.framework   = framework or _detect_framework()
    state.storage     = storage
    state.bus         = EventBus(flags=state.flags)
    state.timeline    = TimelineService(state.bus, flags=state.flags, storage=storage)
    state.initialised = True
