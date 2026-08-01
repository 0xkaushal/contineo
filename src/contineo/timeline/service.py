"""
Timeline Service.

Subscribes to the Event Bus and builds a per-session execution waterfall
from the stream of runtime events.

Responsibilities:
  - Open a TimelineEntry when a *.started event arrives.
  - Close it (set status, duration, metadata) when the matching
    *.completed or *.failed event arrives.
  - Expose get_timeline(session_id) for the dashboard / API layer.

This service NEVER:
  - Calls Analytics, Replay, or Cost directly.
  - Executes the agent.
  - Stores raw prompt/output payloads (that is Replay's job).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import timezone

from contineo.bus.event_bus import EventBus
from contineo.bus.flags import FeatureFlags
from contineo.events.base import BaseEvent, EventType
from contineo.events.context import ContextLoadedEvent
from contineo.events.error import ErrorEvent
from contineo.events.llm import LLMCompletedEvent, LLMStartedEvent
from contineo.events.memory import MemoryReadEvent, MemoryWriteEvent
from contineo.events.session import SessionFinishedEvent, SessionStartedEvent
from contineo.events.stt import STTCompletedEvent, STTStartedEvent
from contineo.events.tool import ToolCalledEvent, ToolCompletedEvent, ToolFailedEvent
from contineo.events.tts import TTSCompletedEvent, TTSStartedEvent
from contineo.timeline.models import SpanKind, SpanStatus, Timeline, TimelineEntry

logger = logging.getLogger("contineo.timeline")


class TimelineService:
    """Builds execution timelines from Event Bus events.

    Each agent session gets its own Timeline object.  The service
    maintains two internal structures per session:

    ``_timelines``   — session_id → Timeline (completed entries)
    ``_open_spans``  — span_id    → TimelineEntry (in-progress entries)

    When a ``*.completed`` or ``*.failed`` event arrives, the matching
    open span is closed and moved into the session's Timeline.

    Args:
        bus:     The EventBus instance to subscribe to.
        flags:   Feature flags. If ``flags.timeline`` is False the service
                 registers no handlers and is effectively a no-op.
        storage: Optional storage backend. When provided, every closed span
                 and every completed session is persisted automatically.
    """

    def __init__(
        self,
        bus: EventBus,
        flags: FeatureFlags | None = None,
        storage=None,
    ) -> None:
        self._flags = flags or FeatureFlags.load()
        self._timelines: dict[str, Timeline] = {}
        self._open_spans: dict[str, TimelineEntry] = {}
        self._storage = storage  # StorageBackend | None

        if not self._flags.timeline:
            logger.info(
                "TimelineService disabled by feature flag",
                extra={"service": "timeline"},
            )
            return

        # Session
        bus.subscribe(EventType.SESSION_STARTED, self._on_session_started)
        bus.subscribe(EventType.SESSION_FINISHED, self._on_session_finished)
        # LLM
        bus.subscribe(EventType.LLM_STARTED, self._on_llm_started)
        bus.subscribe(EventType.LLM_COMPLETED, self._on_llm_completed)
        # Tool
        bus.subscribe(EventType.TOOL_CALLED, self._on_tool_called)
        bus.subscribe(EventType.TOOL_COMPLETED, self._on_tool_completed)
        bus.subscribe(EventType.TOOL_FAILED, self._on_tool_failed)
        # TTS
        bus.subscribe(EventType.TTS_STARTED, self._on_tts_started)
        bus.subscribe(EventType.TTS_COMPLETED, self._on_tts_completed)
        # STT
        bus.subscribe(EventType.STT_STARTED, self._on_stt_started)
        bus.subscribe(EventType.STT_COMPLETED, self._on_stt_completed)
        # Memory (instant — no started/completed pair)
        bus.subscribe(EventType.MEMORY_READ, self._on_memory_read)
        bus.subscribe(EventType.MEMORY_WRITE, self._on_memory_write)
        # Context (instant)
        bus.subscribe(EventType.CONTEXT_LOADED, self._on_context_loaded)
        # Error
        bus.subscribe(EventType.ERROR, self._on_error)

        logger.info(
            "TimelineService started",
            extra={"service": "timeline"},
        )

    # ------------------------------------------------------------------
    # Public query API
    # ------------------------------------------------------------------

    def get_timeline(self, session_id: str) -> Timeline | None:
        """Return the timeline for a session, or None if not found.

        The returned Timeline contains entries sorted by start time
        via its ``sorted_entries`` property.

        Args:
            session_id: The session identifier.

        Returns:
            A Timeline instance, or None if no events have been seen
            for this session yet.
        """
        return self._timelines.get(session_id)

    def get_open_spans(self, session_id: str) -> list[TimelineEntry]:
        """Return spans that are still in-progress for a session.

        Useful for live dashboard updates — these are operations that
        have started but not yet produced a completion event.

        Args:
            session_id: The session identifier.

        Returns:
            List of in-progress TimelineEntry objects.
        """
        return [e for e in self._open_spans.values() if e.session_id == session_id]

    @property
    def session_ids(self) -> list[str]:
        """All session IDs that have timeline data."""
        return list(self._timelines.keys())

    # ------------------------------------------------------------------
    # Session handlers
    # ------------------------------------------------------------------

    async def _on_session_started(self, event: SessionStartedEvent) -> None:
        self._ensure_timeline(event.session_id)
        entry = self._open_span(
            span_id=event.span_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.SESSION,
            label=f"Session: {event.agent_name}",
            started_at=event.timestamp,
            metadata={
                "agent_name": event.agent_name,
                "framework": event.framework.value,
                "input": event.input,
                "tags": event.tags,
            },
        )
        self._log_span_opened(entry, event)

    async def _on_session_finished(self, event: SessionFinishedEvent) -> None:
        entry = self._close_span(
            span_id=event.span_id,
            finished_at=event.timestamp,
            duration_ms=event.duration_ms,
            status=SpanStatus.COMPLETED if event.success else SpanStatus.FAILED,
            extra_metadata={
                "output": event.output,
                "success": event.success,
                "total_tokens": event.total_tokens,
                "total_cost_usd": event.total_cost_usd,
                "agent_name": event.agent_name,
                "project_id": event.project_id,
            },
            error=event.error_message if not event.success else None,
        )
        if entry:
            timeline = self._timelines[event.session_id]
            object.__setattr__(timeline, "is_complete", True)
            if event.duration_ms is not None:
                object.__setattr__(timeline, "total_ms", event.duration_ms)
            self._log_span_closed(entry, event)

            # Persist the full session to storage
            if self._storage is not None:
                from contineo.sdk.utils import fire
                fire(self._storage.save_session(timeline))

    # ------------------------------------------------------------------
    # LLM handlers
    # ------------------------------------------------------------------

    async def _on_llm_started(self, event: LLMStartedEvent) -> None:
        self._ensure_timeline(event.session_id)
        entry = self._open_span(
            span_id=event.span_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.LLM,
            label=f"LLM: {event.model}",
            started_at=event.timestamp,
            metadata={
                "model": event.model,
                "provider": event.provider,
                "temperature": event.temperature,
                "max_tokens": event.max_tokens,
                "message_count": len(event.messages),
            },
        )
        self._log_span_opened(entry, event)

    async def _on_llm_completed(self, event: LLMCompletedEvent) -> None:
        entry = self._close_span(
            span_id=event.span_id,
            finished_at=event.timestamp,
            duration_ms=event.duration_ms,
            status=SpanStatus.COMPLETED,
            extra_metadata={
                "prompt_tokens": event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
                "total_tokens": event.total_tokens,
                "cost_usd": event.cost_usd,
                "finish_reason": event.finish_reason,
                "tool_call_count": len(event.tool_calls),
            },
        )
        if entry:
            self._log_span_closed(entry, event)

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    async def _on_tool_called(self, event: ToolCalledEvent) -> None:
        self._ensure_timeline(event.session_id)
        # Tools use call_id as the correlation key, not span_id,
        # because a single span may contain multiple tool calls.
        entry = self._open_span(
            span_id=event.call_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.TOOL,
            label=f"Tool: {event.tool_name}",
            started_at=event.timestamp,
            metadata={
                "tool_name": event.tool_name,
                "tool_input": event.tool_input,
            },
        )
        self._log_span_opened(entry, event)

    async def _on_tool_completed(self, event: ToolCompletedEvent) -> None:
        entry = self._close_span(
            span_id=event.call_id,
            finished_at=event.timestamp,
            duration_ms=event.duration_ms,
            status=SpanStatus.COMPLETED,
            extra_metadata={"tool_output": event.tool_output},
        )
        if entry:
            self._log_span_closed(entry, event)

    async def _on_tool_failed(self, event: ToolFailedEvent) -> None:
        entry = self._close_span(
            span_id=event.call_id,
            finished_at=event.timestamp,
            duration_ms=event.duration_ms,
            status=SpanStatus.FAILED,
            extra_metadata={"error_type": event.error_type},
            error=event.error_message,
        )
        if entry:
            self._log_span_closed(entry, event)

    # ------------------------------------------------------------------
    # TTS handlers
    # ------------------------------------------------------------------

    async def _on_tts_started(self, event: TTSStartedEvent) -> None:
        self._ensure_timeline(event.session_id)
        entry = self._open_span(
            span_id=event.span_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.TTS,
            label=f"TTS: {event.provider}",
            started_at=event.timestamp,
            metadata={
                "provider": event.provider,
                "voice_id": event.voice_id,
                "language": event.language,
                "char_count": len(event.text),
            },
        )
        self._log_span_opened(entry, event)

    async def _on_tts_completed(self, event: TTSCompletedEvent) -> None:
        entry = self._close_span(
            span_id=event.span_id,
            finished_at=event.timestamp,
            duration_ms=event.duration_ms,
            status=SpanStatus.COMPLETED,
            extra_metadata={
                "audio_duration_ms": event.audio_duration_ms,
                "characters": event.characters,
                "cost_usd": event.cost_usd,
            },
        )
        if entry:
            self._log_span_closed(entry, event)

    # ------------------------------------------------------------------
    # STT handlers
    # ------------------------------------------------------------------

    async def _on_stt_started(self, event: STTStartedEvent) -> None:
        self._ensure_timeline(event.session_id)
        entry = self._open_span(
            span_id=event.span_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.STT,
            label=f"STT: {event.provider}",
            started_at=event.timestamp,
            metadata={
                "provider": event.provider,
                "language": event.language,
                "audio_duration_ms": event.audio_duration_ms,
            },
        )
        self._log_span_opened(entry, event)

    async def _on_stt_completed(self, event: STTCompletedEvent) -> None:
        entry = self._close_span(
            span_id=event.span_id,
            finished_at=event.timestamp,
            duration_ms=event.duration_ms,
            status=SpanStatus.COMPLETED,
            extra_metadata={
                "language_detected": event.language_detected,
                "confidence": event.confidence,
                "cost_usd": event.cost_usd,
            },
        )
        if entry:
            self._log_span_closed(entry, event)

    # ------------------------------------------------------------------
    # Memory handlers (instant — no open/close pair)
    # ------------------------------------------------------------------

    async def _on_memory_read(self, event: MemoryReadEvent) -> None:
        self._ensure_timeline(event.session_id)
        entry = self._instant_span(
            span_id=event.span_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.MEMORY,
            label=f"Memory Read: {event.memory_key}",
            timestamp=event.timestamp,
            duration_ms=event.duration_ms,
            metadata={
                "memory_key": event.memory_key,
                "memory_type": event.memory_type,
                "operation": "read",
            },
        )
        self._commit_entry(entry)

    async def _on_memory_write(self, event: MemoryWriteEvent) -> None:
        self._ensure_timeline(event.session_id)
        entry = self._instant_span(
            span_id=event.span_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.MEMORY,
            label=f"Memory Write: {event.memory_key}",
            timestamp=event.timestamp,
            duration_ms=event.duration_ms,
            metadata={
                "memory_key": event.memory_key,
                "memory_type": event.memory_type,
                "operation": "write",
            },
        )
        self._commit_entry(entry)

    # ------------------------------------------------------------------
    # Context handler (instant)
    # ------------------------------------------------------------------

    async def _on_context_loaded(self, event: ContextLoadedEvent) -> None:
        self._ensure_timeline(event.session_id)
        entry = self._instant_span(
            span_id=event.span_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.CONTEXT,
            label=f"Context: {event.source}",
            timestamp=event.timestamp,
            duration_ms=event.duration_ms,
            metadata={
                "context_type": event.context_type,
                "source": event.source,
                "token_count": event.token_count,
                "truncated": event.truncated,
            },
        )
        self._commit_entry(entry)

    # ------------------------------------------------------------------
    # Error handler
    # ------------------------------------------------------------------

    async def _on_error(self, event: ErrorEvent) -> None:
        self._ensure_timeline(event.session_id)
        entry = self._instant_span(
            span_id=event.span_id,
            trace_id=event.trace_id,
            session_id=event.session_id,
            kind=SpanKind.ERROR,
            label=f"Error: {event.error_type}",
            timestamp=event.timestamp,
            duration_ms=None,
            metadata={
                "error_type": event.error_type,
                "recoverable": event.recoverable,
                "source_event_type": event.source_event_type,
                "source_event_id": event.source_event_id,
            },
            status=SpanStatus.FAILED,
            error=event.error_message,
        )
        self._commit_entry(entry)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_timeline(self, session_id: str) -> None:
        """Create a Timeline for a session if one does not exist yet."""
        if session_id not in self._timelines:
            self._timelines[session_id] = Timeline(session_id=session_id)

    def _open_span(
        self,
        *,
        span_id: str,
        trace_id: str,
        session_id: str,
        kind: SpanKind,
        label: str,
        started_at,
        metadata: dict,
    ) -> TimelineEntry:
        """Create an in-progress entry and park it in ``_open_spans``."""
        entry = TimelineEntry(
            span_id=span_id,
            trace_id=trace_id,
            session_id=session_id,
            kind=kind,
            label=label,
            status=SpanStatus.IN_PROGRESS,
            started_at=started_at,
            metadata=metadata,
        )
        self._open_spans[span_id] = entry
        return entry

    def _close_span(
        self,
        *,
        span_id: str,
        finished_at,
        duration_ms: float | None,
        status: SpanStatus,
        extra_metadata: dict | None = None,
        error: str | None = None,
    ) -> TimelineEntry | None:
        """Close an open span and move it into its session's Timeline.

        Returns the closed entry, or None if the span_id was not found
        (e.g. a completed event arrived without a prior started event).
        """
        open_entry = self._open_spans.pop(span_id, None)
        if open_entry is None:
            logger.warning(
                "Received completion for unknown span — possible missed started event",
                extra={
                    "span_id": span_id,
                    "service": "timeline",
                },
            )
            return None

        merged_meta = {**open_entry.metadata, **(extra_metadata or {})}

        # Compute duration from timestamps if not provided
        if duration_ms is None and finished_at is not None:
            delta = finished_at - open_entry.started_at
            duration_ms = delta.total_seconds() * 1000

        closed_entry = TimelineEntry(
            span_id=open_entry.span_id,
            trace_id=open_entry.trace_id,
            session_id=open_entry.session_id,
            kind=open_entry.kind,
            label=open_entry.label,
            status=status,
            started_at=open_entry.started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            metadata=merged_meta,
            error=error,
        )
        self._commit_entry(closed_entry)
        return closed_entry

    def _instant_span(
        self,
        *,
        span_id: str,
        trace_id: str,
        session_id: str,
        kind: SpanKind,
        label: str,
        timestamp,
        duration_ms: float | None,
        metadata: dict,
        status: SpanStatus = SpanStatus.COMPLETED,
        error: str | None = None,
    ) -> TimelineEntry:
        """Create a span that has no separate started/completed pair."""
        return TimelineEntry(
            span_id=span_id,
            trace_id=trace_id,
            session_id=session_id,
            kind=kind,
            label=label,
            status=status,
            started_at=timestamp,
            finished_at=timestamp,
            duration_ms=duration_ms,
            metadata=metadata,
            error=error,
        )

    def _commit_entry(self, entry: TimelineEntry) -> None:
        """Append a closed entry to its session's Timeline and persist it."""
        timeline = self._timelines.get(entry.session_id)
        if timeline is None:
            self._ensure_timeline(entry.session_id)
            timeline = self._timelines[entry.session_id]
        timeline.entries.append(entry)

        # Persist the span if a storage backend is configured
        if self._storage is not None:
            import asyncio
            from contineo.sdk.utils import fire
            fire(self._storage.save_span(entry))

    # ------------------------------------------------------------------
    # Logging helpers
    # ------------------------------------------------------------------

    def _log_span_opened(self, entry: TimelineEntry, event: BaseEvent) -> None:
        logger.debug(
            "Span opened",
            extra={
                "span_id": entry.span_id,
                "kind": entry.kind.value,
                "label": entry.label,
                "session_id": event.session_id,
                "trace_id": event.trace_id,
                "service": "timeline",
            },
        )

    def _log_span_closed(self, entry: TimelineEntry, event: BaseEvent) -> None:
        logger.debug(
            "Span closed",
            extra={
                "span_id": entry.span_id,
                "kind": entry.kind.value,
                "status": entry.status.value,
                "duration_ms": entry.duration_ms,
                "session_id": event.session_id,
                "trace_id": event.trace_id,
                "service": "timeline",
            },
        )
