"""contineo - Run Time Intelligence"""

__version__ = "0.1.1"

# ---------------------------------------------------------------------------
# Primary SDK surface — the three things most developers ever need
# ---------------------------------------------------------------------------
from contineo.sdk import init, observe, attach, get_timeline, last_session_id
from contineo.storage import StorageBackend, SqliteStorage, PostgresStorage, connect

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
    "attach",
    "observe",
    "get_timeline",
    "last_session_id",
    # Storage
    "StorageBackend",
    "SqliteStorage",
    "PostgresStorage",
    "connect",
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

