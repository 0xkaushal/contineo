"""
Contineo Observe — SDK: global state container.
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
        self.storage = None  # StorageBackend | None

    def require_init(self) -> None:
        if not self.initialised:
            raise RuntimeError(
                "Contineo is not initialised. Call contineo.init(project_id=...) "
                "before using @contineo.observe."
            )


state = _SDKState()
