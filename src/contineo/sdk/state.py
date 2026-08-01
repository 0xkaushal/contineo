"""
Contineo Observe — SDK: global state container.

_SDKState holds the single shared instance of the bus, timeline,
and config that every SDK call works against.
"""

from __future__ import annotations

from contineo.bus.event_bus import EventBus
from contineo.bus.flags import FeatureFlags
from contineo.events.base import Framework
from contineo.timeline.service import TimelineService


class _SDKState:
    def __init__(self) -> None:
        self.initialised: bool = False
        self.project_id: str = "default"
        self.bus: EventBus | None = None
        self.timeline: TimelineService | None = None
        self.framework: Framework = Framework.UNKNOWN
        self.flags: FeatureFlags = FeatureFlags.load()
        self._last_session_id: str | None = None

    def require_init(self) -> None:
        if not self.initialised:
            raise RuntimeError(
                "Contineo is not initialised. Call contineo.init(project_id=...) "
                "before using @contineo.observe."
            )


# Single global instance — created at import time, populated by init()
state = _SDKState()
