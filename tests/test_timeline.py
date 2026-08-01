"""Unit tests for TimelineService."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from contineo.bus.event_bus import EventBus
from contineo.bus.flags import FeatureFlags
from contineo.events.base import EventType, Framework
from contineo.events.context import ContextLoadedEvent
from contineo.events.error import ErrorEvent
from contineo.events.llm import LLMCompletedEvent, LLMStartedEvent
from contineo.events.memory import MemoryReadEvent, MemoryWriteEvent
from contineo.events.session import SessionFinishedEvent, SessionStartedEvent
from contineo.events.stt import STTCompletedEvent, STTStartedEvent
from contineo.events.tool import ToolCalledEvent, ToolCompletedEvent, ToolFailedEvent
from contineo.events.tts import TTSCompletedEvent, TTSStartedEvent
from contineo.timeline.models import SpanKind, SpanStatus
from contineo.timeline.service import TimelineService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def ts(offset_ms: float) -> datetime:
    """Return T0 + offset_ms milliseconds."""
    return T0 + timedelta(milliseconds=offset_ms)


def common(*, span_id: str | None = None, session_id: str = "sess-1") -> dict:
    return dict(
        project_id="proj-1",
        session_id=session_id,
        trace_id="trace-1",
        span_id=span_id or str(uuid.uuid4()),
        agent_name="test-agent",
        framework=Framework.LANGGRAPH,
    )


# ---------------------------------------------------------------------------
# Fixture: bus + timeline wired together
# ---------------------------------------------------------------------------


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def timeline(bus):
    return TimelineService(bus)


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


class TestSessionTimeline:
    @pytest.mark.asyncio
    async def test_session_started_creates_in_progress_span(self, bus, timeline):
        span_id = "span-sess"
        await bus.publish(SessionStartedEvent(**common(span_id=span_id), timestamp=T0))

        open_spans = timeline.get_open_spans("sess-1")
        assert len(open_spans) == 1
        assert open_spans[0].kind == SpanKind.SESSION
        assert open_spans[0].status == SpanStatus.IN_PROGRESS

    @pytest.mark.asyncio
    async def test_session_finished_closes_span(self, bus, timeline):
        span_id = "span-sess"
        await bus.publish(SessionStartedEvent(**common(span_id=span_id), timestamp=T0))
        await bus.publish(
            SessionFinishedEvent(
                **common(span_id=span_id),
                timestamp=ts(1000),
                duration_ms=1000,
                success=True,
                output="done",
            )
        )

        tl = timeline.get_timeline("sess-1")
        assert tl is not None
        assert tl.is_complete is True
        assert tl.total_ms == 1000.0

        entry = tl.get_entry(span_id)
        assert entry is not None
        assert entry.status == SpanStatus.COMPLETED
        assert entry.duration_ms == 1000.0
        assert entry.metadata["output"] == "done"

    @pytest.mark.asyncio
    async def test_session_finished_failure_sets_failed_status(self, bus, timeline):
        span_id = "span-sess"
        await bus.publish(SessionStartedEvent(**common(span_id=span_id), timestamp=T0))
        await bus.publish(
            SessionFinishedEvent(
                **common(span_id=span_id),
                timestamp=ts(500),
                success=False,
                error_message="Agent crashed",
            )
        )

        tl = timeline.get_timeline("sess-1")
        entry = tl.get_entry(span_id)
        assert entry.status == SpanStatus.FAILED
        assert entry.error == "Agent crashed"

    @pytest.mark.asyncio
    async def test_no_open_spans_after_session_finished(self, bus, timeline):
        span_id = "span-sess"
        await bus.publish(SessionStartedEvent(**common(span_id=span_id), timestamp=T0))
        await bus.publish(
            SessionFinishedEvent(**common(span_id=span_id), timestamp=ts(100))
        )
        assert timeline.get_open_spans("sess-1") == []


# ---------------------------------------------------------------------------
# LLM lifecycle
# ---------------------------------------------------------------------------


class TestLLMTimeline:
    @pytest.mark.asyncio
    async def test_llm_started_opens_span(self, bus, timeline):
        span_id = "span-llm"
        await bus.publish(
            LLMStartedEvent(**common(span_id=span_id), model="gpt-4o", provider="openai", timestamp=T0)
        )
        open_spans = timeline.get_open_spans("sess-1")
        assert any(s.kind == SpanKind.LLM for s in open_spans)

    @pytest.mark.asyncio
    async def test_llm_completed_closes_span_with_tokens(self, bus, timeline):
        span_id = "span-llm"
        await bus.publish(
            LLMStartedEvent(**common(span_id=span_id), model="gpt-4o", provider="openai", timestamp=T0)
        )
        await bus.publish(
            LLMCompletedEvent(
                **common(span_id=span_id),
                model="gpt-4o",
                provider="openai",
                timestamp=ts(800),
                duration_ms=800,
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                finish_reason="stop",
            )
        )

        tl = timeline.get_timeline("sess-1")
        entry = tl.get_entry(span_id)
        assert entry.status == SpanStatus.COMPLETED
        assert entry.duration_ms == 800.0
        assert entry.metadata["total_tokens"] == 150
        assert entry.metadata["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_llm_duration_computed_from_timestamps_if_not_provided(self, bus, timeline):
        span_id = "span-llm"
        await bus.publish(
            LLMStartedEvent(**common(span_id=span_id), model="gpt-4o", provider="openai", timestamp=T0)
        )
        await bus.publish(
            LLMCompletedEvent(
                **common(span_id=span_id),
                model="gpt-4o",
                provider="openai",
                timestamp=ts(600),
                duration_ms=None,  # not provided
            )
        )

        entry = timeline.get_timeline("sess-1").get_entry(span_id)
        assert entry.duration_ms == pytest.approx(600.0)

    @pytest.mark.asyncio
    async def test_llm_label_includes_model_name(self, bus, timeline):
        span_id = "span-llm"
        await bus.publish(
            LLMStartedEvent(**common(span_id=span_id), model="claude-3-5-sonnet", provider="anthropic", timestamp=T0)
        )
        open_spans = timeline.get_open_spans("sess-1")
        assert open_spans[0].label == "LLM: claude-3-5-sonnet"


# ---------------------------------------------------------------------------
# Tool lifecycle
# ---------------------------------------------------------------------------


class TestToolTimeline:
    @pytest.mark.asyncio
    async def test_tool_called_opens_span_keyed_by_call_id(self, bus, timeline):
        await bus.publish(
            ToolCalledEvent(
                **common(),
                tool_name="weather_search",
                call_id="call-001",
                timestamp=T0,
            )
        )
        open_spans = timeline.get_open_spans("sess-1")
        assert len(open_spans) == 1
        assert open_spans[0].kind == SpanKind.TOOL
        assert open_spans[0].span_id == "call-001"

    @pytest.mark.asyncio
    async def test_tool_completed_closes_span(self, bus, timeline):
        await bus.publish(
            ToolCalledEvent(**common(), tool_name="search", call_id="call-001", timestamp=T0)
        )
        await bus.publish(
            ToolCompletedEvent(
                **common(),
                tool_name="search",
                call_id="call-001",
                timestamp=ts(300),
                duration_ms=300,
                tool_output={"result": "Paris"},
            )
        )

        tl = timeline.get_timeline("sess-1")
        entry = tl.get_entry("call-001")
        assert entry.status == SpanStatus.COMPLETED
        assert entry.metadata["tool_output"] == {"result": "Paris"}

    @pytest.mark.asyncio
    async def test_tool_failed_sets_failed_status(self, bus, timeline):
        await bus.publish(
            ToolCalledEvent(**common(), tool_name="search", call_id="call-002", timestamp=T0)
        )
        await bus.publish(
            ToolFailedEvent(
                **common(),
                tool_name="search",
                call_id="call-002",
                timestamp=ts(100),
                error_type="TimeoutError",
                error_message="Search timed out",
            )
        )

        entry = timeline.get_timeline("sess-1").get_entry("call-002")
        assert entry.status == SpanStatus.FAILED
        assert entry.error == "Search timed out"
        assert entry.metadata["error_type"] == "TimeoutError"

    @pytest.mark.asyncio
    async def test_multiple_tool_calls_tracked_independently(self, bus, timeline):
        for i in range(3):
            await bus.publish(
                ToolCalledEvent(**common(), tool_name=f"tool-{i}", call_id=f"call-{i}", timestamp=ts(i * 100))
            )
        assert len(timeline.get_open_spans("sess-1")) == 3

        for i in range(3):
            await bus.publish(
                ToolCompletedEvent(**common(), tool_name=f"tool-{i}", call_id=f"call-{i}", timestamp=ts(i * 100 + 50))
            )
        assert timeline.get_open_spans("sess-1") == []
        assert len(timeline.get_timeline("sess-1").entries) == 3


# ---------------------------------------------------------------------------
# TTS lifecycle
# ---------------------------------------------------------------------------


class TestTTSTimeline:
    @pytest.mark.asyncio
    async def test_tts_span_opened_and_closed(self, bus, timeline):
        span_id = "span-tts"
        await bus.publish(
            TTSStartedEvent(**common(span_id=span_id), provider="elevenlabs", text="Hello!", timestamp=T0)
        )
        await bus.publish(
            TTSCompletedEvent(
                **common(span_id=span_id),
                provider="elevenlabs",
                timestamp=ts(200),
                duration_ms=200,
                characters=6,
                audio_duration_ms=1500,
                cost_usd=0.001,
            )
        )

        entry = timeline.get_timeline("sess-1").get_entry(span_id)
        assert entry.kind == SpanKind.TTS
        assert entry.status == SpanStatus.COMPLETED
        assert entry.metadata["characters"] == 6
        assert entry.metadata["audio_duration_ms"] == 1500


# ---------------------------------------------------------------------------
# STT lifecycle
# ---------------------------------------------------------------------------


class TestSTTTimeline:
    @pytest.mark.asyncio
    async def test_stt_span_opened_and_closed(self, bus, timeline):
        span_id = "span-stt"
        await bus.publish(
            STTStartedEvent(**common(span_id=span_id), provider="deepgram", timestamp=T0)
        )
        await bus.publish(
            STTCompletedEvent(
                **common(span_id=span_id),
                provider="deepgram",
                timestamp=ts(400),
                duration_ms=400,
                transcript="What is the weather?",
                confidence=0.98,
            )
        )

        entry = timeline.get_timeline("sess-1").get_entry(span_id)
        assert entry.kind == SpanKind.STT
        assert entry.status == SpanStatus.COMPLETED
        assert entry.metadata["confidence"] == 0.98


# ---------------------------------------------------------------------------
# Instant spans — Memory, Context, Error
# ---------------------------------------------------------------------------


class TestInstantSpans:
    @pytest.mark.asyncio
    async def test_memory_read_creates_completed_span(self, bus, timeline):
        await bus.publish(
            MemoryReadEvent(**common(), memory_key="user_prefs", timestamp=T0)
        )
        tl = timeline.get_timeline("sess-1")
        assert len(tl.entries) == 1
        assert tl.entries[0].kind == SpanKind.MEMORY
        assert tl.entries[0].status == SpanStatus.COMPLETED
        assert tl.entries[0].metadata["operation"] == "read"

    @pytest.mark.asyncio
    async def test_memory_write_creates_completed_span(self, bus, timeline):
        await bus.publish(
            MemoryWriteEvent(**common(), memory_key="user_prefs", value="dark", timestamp=T0)
        )
        tl = timeline.get_timeline("sess-1")
        assert tl.entries[0].metadata["operation"] == "write"

    @pytest.mark.asyncio
    async def test_context_loaded_creates_completed_span(self, bus, timeline):
        await bus.publish(
            ContextLoadedEvent(**common(), context_type="document", source="policy.pdf", timestamp=T0)
        )
        tl = timeline.get_timeline("sess-1")
        assert tl.entries[0].kind == SpanKind.CONTEXT
        assert tl.entries[0].metadata["source"] == "policy.pdf"

    @pytest.mark.asyncio
    async def test_error_creates_failed_span(self, bus, timeline):
        await bus.publish(
            ErrorEvent(
                **common(),
                error_type="ValueError",
                error_message="Bad input",
                timestamp=T0,
            )
        )
        tl = timeline.get_timeline("sess-1")
        assert tl.entries[0].kind == SpanKind.ERROR
        assert tl.entries[0].status == SpanStatus.FAILED
        assert tl.entries[0].error == "Bad input"


# ---------------------------------------------------------------------------
# Waterfall ordering
# ---------------------------------------------------------------------------


class TestWaterfallOrdering:
    @pytest.mark.asyncio
    async def test_sorted_entries_returns_chronological_order(self, bus, timeline):
        # Publish events out of order and verify sorted_entries is correct
        sess_span = "span-sess"
        llm_span = "span-llm"
        tool_call_id = "call-001"

        # Publish in a non-sequential order
        await bus.publish(
            ToolCalledEvent(**common(), tool_name="search", call_id=tool_call_id, timestamp=ts(200))
        )
        await bus.publish(
            LLMStartedEvent(**common(span_id=llm_span), model="gpt-4o", provider="openai", timestamp=ts(100))
        )
        await bus.publish(
            SessionStartedEvent(**common(span_id=sess_span), timestamp=T0)
        )

        # Close them
        await bus.publish(
            ToolCompletedEvent(**common(), tool_name="search", call_id=tool_call_id, timestamp=ts(450))
        )
        await bus.publish(
            LLMCompletedEvent(**common(span_id=llm_span), model="gpt-4o", provider="openai", timestamp=ts(500))
        )
        await bus.publish(
            SessionFinishedEvent(**common(span_id=sess_span), timestamp=ts(600), duration_ms=600)
        )

        tl = timeline.get_timeline("sess-1")
        sorted_entries = tl.sorted_entries
        start_times = [e.started_at for e in sorted_entries]
        assert start_times == sorted(start_times)

    @pytest.mark.asyncio
    async def test_full_session_waterfall_entry_count(self, bus, timeline):
        """A complete session with 1 LLM call and 2 tool calls = 4 entries."""
        sess = "span-sess"
        llm = "span-llm"

        await bus.publish(SessionStartedEvent(**common(span_id=sess), timestamp=T0))
        await bus.publish(LLMStartedEvent(**common(span_id=llm), model="gpt-4o", provider="openai", timestamp=ts(10)))
        await bus.publish(ToolCalledEvent(**common(), tool_name="t1", call_id="c1", timestamp=ts(100)))
        await bus.publish(ToolCalledEvent(**common(), tool_name="t2", call_id="c2", timestamp=ts(200)))
        await bus.publish(ToolCompletedEvent(**common(), tool_name="t1", call_id="c1", timestamp=ts(300)))
        await bus.publish(ToolCompletedEvent(**common(), tool_name="t2", call_id="c2", timestamp=ts(350)))
        await bus.publish(LLMCompletedEvent(**common(span_id=llm), model="gpt-4o", provider="openai", timestamp=ts(400)))
        await bus.publish(SessionFinishedEvent(**common(span_id=sess), timestamp=ts(500), duration_ms=500))

        tl = timeline.get_timeline("sess-1")
        assert len(tl.entries) == 4  # session + llm + tool1 + tool2
        assert tl.is_complete is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_completed_without_started_logs_warning_and_returns_none(self, bus, timeline, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="contineo.timeline"):
            await bus.publish(
                LLMCompletedEvent(
                    **common(span_id="orphan-span"),
                    model="gpt-4o",
                    provider="openai",
                    timestamp=T0,
                )
            )
        assert any("unknown span" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_event_before_session_started_still_tracked(self, bus, timeline):
        """An event arriving before session.started creates the timeline implicitly."""
        await bus.publish(
            LLMStartedEvent(**common(span_id="span-llm"), model="gpt-4o", provider="openai", timestamp=T0)
        )
        assert "sess-1" in timeline.session_ids

    @pytest.mark.asyncio
    async def test_multiple_sessions_are_isolated(self, bus, timeline):
        await bus.publish(
            SessionStartedEvent(**common(span_id="s1", session_id="sess-A"), timestamp=T0)
        )
        await bus.publish(
            SessionStartedEvent(**common(span_id="s2", session_id="sess-B"), timestamp=T0)
        )

        assert timeline.get_timeline("sess-A") is not None
        assert timeline.get_timeline("sess-B") is not None
        assert len(timeline.get_open_spans("sess-A")) == 1
        assert len(timeline.get_open_spans("sess-B")) == 1

    @pytest.mark.asyncio
    async def test_unknown_session_returns_none(self, bus, timeline):
        assert timeline.get_timeline("no-such-session") is None


# ---------------------------------------------------------------------------
# Feature flag — timeline disabled
# ---------------------------------------------------------------------------


class TestFeatureFlag:
    @pytest.mark.asyncio
    async def test_disabled_timeline_service_does_not_record(self):
        flags = FeatureFlags()
        flags.timeline = False
        bus = EventBus(flags=flags)
        svc = TimelineService(bus, flags=flags)

        await bus.publish(SessionStartedEvent(**common(), timestamp=T0))
        assert svc.get_timeline("sess-1") is None
        assert svc.session_ids == []
