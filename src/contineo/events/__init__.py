"""
Contineo Observe — Event Schema

All runtime events flow through this schema.
Every service derives state from these immutable event objects.
"""

from contineo.events.base import BaseEvent, EventType, Framework
from contineo.events.session import SessionStartedEvent, SessionFinishedEvent
from contineo.events.llm import LLMStartedEvent, LLMCompletedEvent
from contineo.events.tool import ToolCalledEvent, ToolCompletedEvent, ToolFailedEvent
from contineo.events.tts import TTSStartedEvent, TTSCompletedEvent
from contineo.events.stt import STTStartedEvent, STTCompletedEvent
from contineo.events.memory import MemoryReadEvent, MemoryWriteEvent
from contineo.events.context import ContextLoadedEvent
from contineo.events.error import ErrorEvent

__all__ = [
    # Base
    "BaseEvent",
    "EventType",
    "Framework",
    # Session
    "SessionStartedEvent",
    "SessionFinishedEvent",
    # LLM
    "LLMStartedEvent",
    "LLMCompletedEvent",
    # Tool
    "ToolCalledEvent",
    "ToolCompletedEvent",
    "ToolFailedEvent",
    # TTS
    "TTSStartedEvent",
    "TTSCompletedEvent",
    # STT
    "STTStartedEvent",
    "STTCompletedEvent",
    # Memory
    "MemoryReadEvent",
    "MemoryWriteEvent",
    # Context
    "ContextLoadedEvent",
    # Error
    "ErrorEvent",
]
