"""
Timeline data models.

These are the internal representations used by TimelineService.
They are NOT event models — they are derived state built from events.

A Timeline is a collection of TimelineEntries for a single session.
Each TimelineEntry represents one span (a started → completed/failed pair).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SpanKind(str, Enum):
    """The kind of operation a timeline span represents."""

    SESSION = "session"
    LLM = "llm"
    TOOL = "tool"
    TTS = "tts"
    STT = "stt"
    MEMORY = "memory"
    CONTEXT = "context"
    ERROR = "error"
    UNKNOWN = "unknown"


class SpanStatus(str, Enum):
    """Whether a span completed successfully, failed, or is still open."""

    IN_PROGRESS = "in_progress"  # started event received, no completion yet
    COMPLETED = "completed"       # matching completed event received
    FAILED = "failed"             # matching failed/error event received


class TimelineEntry(BaseModel):
    """A single span in the execution waterfall.

    A span is opened by a ``*.started`` event and closed by a
    ``*.completed`` or ``*.failed`` event that shares the same
    ``span_id`` (or ``call_id`` for tools).

    Attributes:
        span_id:      The span identifier — matches the originating event.
        trace_id:     Distributed trace identifier.
        session_id:   Session this span belongs to.
        kind:         What kind of operation this span represents.
        label:        Human-readable label shown in the waterfall UI.
        status:       in_progress | completed | failed.
        started_at:   UTC timestamp when the span opened.
        finished_at:  UTC timestamp when the span closed (None if still open).
        duration_ms:  Wall-clock duration in milliseconds (None if still open).
        metadata:     Arbitrary key/value pairs captured from the events
                      (e.g. model name, token counts, tool name, etc.).
        error:        Error message if status is FAILED.
    """

    span_id: str = Field(description="Span identifier")
    trace_id: str = Field(description="Distributed trace identifier")
    session_id: str = Field(description="Session this span belongs to")
    kind: SpanKind = Field(description="Operation kind")
    label: str = Field(description="Human-readable label for the waterfall UI")
    status: SpanStatus = Field(default=SpanStatus.IN_PROGRESS)
    started_at: datetime = Field(description="UTC timestamp when the span opened")
    finished_at: datetime | None = Field(default=None)
    duration_ms: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None)


class Timeline(BaseModel):
    """The complete execution timeline for a single agent session.

    Attributes:
        session_id:  Session identifier.
        entries:     All spans in start-time order.
        total_ms:    Total session wall-clock duration (from session span).
        is_complete: True once a session.finished event has been received.
    """

    session_id: str
    entries: list[TimelineEntry] = Field(default_factory=list)
    total_ms: float | None = Field(default=None)
    is_complete: bool = Field(default=False)

    @property
    def sorted_entries(self) -> list[TimelineEntry]:
        """Entries sorted by start time — the waterfall order."""
        return sorted(self.entries, key=lambda e: e.started_at)

    def get_entry(self, span_id: str) -> TimelineEntry | None:
        """Look up a single entry by span_id."""
        for entry in self.entries:
            if entry.span_id == span_id:
                return entry
        return None
