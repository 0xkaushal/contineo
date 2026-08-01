"""contineo - Run Time Intelligence"""

__version__ = "0.1.1"

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

