"""contineo - Run Time Intelligence"""

__version__ = "0.1.1"

# ---------------------------------------------------------------------------
# Primary SDK surface — the three things most developers ever need
# ---------------------------------------------------------------------------
from contineo.sdk import init, observe, get_timeline, last_session_id

from contineo.events import (
    BaseEvent,
    EventType,
    Framework,
    SessionStartedEvent,
    SessionFinishedEvent,
    LLMStartedEvent,
    LLMCompletedEvent,
    ToolCalledEvent,
    ToolCompletedEvent,
    ToolFailedEvent,
    TTSStartedEvent,
    TTSCompletedEvent,
    STTStartedEvent,
    STTCompletedEvent,
    MemoryReadEvent,
    MemoryWriteEvent,
    ContextLoadedEvent,
    ErrorEvent,
)
from contineo.bus import EventBus, EventBusProtocol, EventHandler, FeatureFlags
from contineo.timeline import TimelineService, Timeline, TimelineEntry, SpanKind, SpanStatus

__all__ = [
    "__version__",
    # Primary SDK
    "init",
    "observe",
    "get_timeline",
    "last_session_id",
    # Events
    "BaseEvent",
    "EventType",
    "Framework",
    "SessionStartedEvent",
    "SessionFinishedEvent",
    "LLMStartedEvent",
    "LLMCompletedEvent",
    "ToolCalledEvent",
    "ToolCompletedEvent",
    "ToolFailedEvent",
    "TTSStartedEvent",
    "TTSCompletedEvent",
    "STTStartedEvent",
    "STTCompletedEvent",
    "MemoryReadEvent",
    "MemoryWriteEvent",
    "ContextLoadedEvent",
    "ErrorEvent",
    # Bus
    "EventBus",
    "EventBusProtocol",
    "EventHandler",
    "FeatureFlags",
    # Timeline
    "TimelineService",
    "Timeline",
    "TimelineEntry",
    "SpanKind",
    "SpanStatus",
]

