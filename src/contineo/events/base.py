"""
Base event model and core enumerations.

Every event emitted by Contineo Observe derives from BaseEvent.
Events are immutable once created — never mutate a published event.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class EventType(str, Enum):
    """All supported runtime event types.

    String-valued so they serialise cleanly to JSON without extra conversion.
    """

    # Session lifecycle
    SESSION_STARTED = "session.started"
    SESSION_FINISHED = "session.finished"

    # LLM lifecycle
    LLM_STARTED = "llm.started"
    LLM_COMPLETED = "llm.completed"

    # Tool lifecycle
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # Text-to-Speech lifecycle
    TTS_STARTED = "tts.started"
    TTS_COMPLETED = "tts.completed"

    # Speech-to-Text lifecycle
    STT_STARTED = "stt.started"
    STT_COMPLETED = "stt.completed"

    # Memory lifecycle
    MEMORY_READ = "memory.read"
    MEMORY_WRITE = "memory.write"

    # Context lifecycle
    CONTEXT_LOADED = "context.loaded"

    # Error
    ERROR = "error"


class Framework(str, Enum):
    """Supported agent frameworks.

    Use CUSTOM for any framework not listed here.
    """

    LANGGRAPH = "langgraph"
    PIPECAT = "pipecat"
    OPENAI = "openai"
    LIVEKIT = "livekit"
    MCP = "mcp"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class BaseEvent(BaseModel):
    """Immutable base class for all Contineo Observe runtime events.

    All fields except ``metadata`` are required at construction time.
    The ``event_id`` and ``timestamp`` are auto-generated when not supplied,
    so callers only need to provide the identifiers meaningful to their session.

    Attributes:
        version:      Schema version. Increment only on breaking changes.
        event_id:     Globally unique identifier for this event instance.
        timestamp:    UTC time the event was created (ISO-8601).
        project_id:   Identifies the project/tenant emitting the event.
        session_id:   Groups all events belonging to a single agent run.
        trace_id:     OpenTelemetry-compatible trace identifier.
        span_id:      OpenTelemetry-compatible span identifier.
        agent_name:   Human-readable name of the agent.
        framework:    Framework that produced this event.
        event_type:   Discriminator — set by each concrete subclass.
        metadata:     Arbitrary key/value pairs for framework-specific extras.
    """

    model_config = {"frozen": True}  # Events are immutable after creation

    version: int = Field(default=1, description="Event schema version")
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Globally unique event identifier (UUID v4)",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of event creation",
    )
    project_id: str = Field(description="Project / tenant identifier")
    session_id: str = Field(description="Agent session identifier")
    trace_id: str = Field(description="Distributed trace identifier")
    span_id: str = Field(description="Span identifier within the trace")
    agent_name: str = Field(description="Human-readable agent name")
    framework: Framework = Field(description="Agent framework that emitted the event")
    event_type: EventType = Field(description="Discriminator for the event kind")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary framework-specific key/value pairs",
    )

    @model_validator(mode="after")
    def _validate_ids_not_empty(self) -> "BaseEvent":
        for field in ("project_id", "session_id", "trace_id", "span_id", "agent_name"):
            if not getattr(self, field).strip():
                raise ValueError(f"'{field}' must not be empty or whitespace")
        return self

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary representation.

        The ``timestamp`` is converted to an ISO-8601 string.
        Enum values are serialised as their string values.
        """
        return self.model_dump(mode="json")

    def to_json(self, *, indent: int | None = None) -> str:
        """Serialise the event to a JSON string.

        Args:
            indent: Optional indentation level for pretty-printing.

        Returns:
            A JSON string representation of the event.
        """
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BaseEvent":
        """Deserialise an event from a dictionary.

        Args:
            data: Dictionary previously produced by ``to_dict()``.

        Returns:
            A validated instance of the calling class.
        """
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, raw: str) -> "BaseEvent":
        """Deserialise an event from a JSON string.

        Args:
            raw: JSON string previously produced by ``to_json()``.

        Returns:
            A validated instance of the calling class.
        """
        return cls.model_validate_json(raw)
