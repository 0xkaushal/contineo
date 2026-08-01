"""Unit tests for Contineo Observe event models."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from contineo.events.base import BaseEvent, EventType, Framework
from contineo.events.context import ContextLoadedEvent
from contineo.events.error import ErrorEvent
from contineo.events.llm import LLMCompletedEvent, LLMStartedEvent
from contineo.events.memory import MemoryReadEvent, MemoryWriteEvent
from contineo.events.session import SessionFinishedEvent, SessionStartedEvent
from contineo.events.stt import STTCompletedEvent, STTStartedEvent
from contineo.events.tool import ToolCalledEvent, ToolCompletedEvent, ToolFailedEvent
from contineo.events.tts import TTSCompletedEvent, TTSStartedEvent

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

COMMON = dict(
    project_id="proj-001",
    session_id="sess-abc",
    trace_id="trace-xyz",
    span_id="span-1",
    agent_name="weather-agent",
    framework=Framework.LANGGRAPH,
)


# ---------------------------------------------------------------------------
# BaseEvent / field defaults
# ---------------------------------------------------------------------------


class TestBaseEventDefaults:
    def test_event_id_is_uuid(self):
        e = SessionStartedEvent(**COMMON)
        uuid.UUID(e.event_id)  # raises if not a valid UUID

    def test_timestamp_is_utc(self):
        e = SessionStartedEvent(**COMMON)
        assert e.timestamp.tzinfo is not None
        assert e.timestamp.tzinfo == timezone.utc

    def test_version_defaults_to_one(self):
        e = SessionStartedEvent(**COMMON)
        assert e.version == 1

    def test_metadata_defaults_to_empty_dict(self):
        e = SessionStartedEvent(**COMMON)
        assert e.metadata == {}

    def test_metadata_accepts_arbitrary_keys(self):
        e = SessionStartedEvent(**COMMON, metadata={"foo": "bar", "nested": {"x": 1}})
        assert e.metadata["foo"] == "bar"

    def test_two_events_have_different_ids(self):
        a = SessionStartedEvent(**COMMON)
        b = SessionStartedEvent(**COMMON)
        assert a.event_id != b.event_id

    def test_event_is_immutable(self):
        e = SessionStartedEvent(**COMMON)
        with pytest.raises((ValidationError, TypeError)):
            e.agent_name = "other-agent"  # type: ignore[misc]


class TestBaseEventValidation:
    @pytest.mark.parametrize("field", ["project_id", "session_id", "trace_id", "span_id", "agent_name"])
    def test_empty_string_raises(self, field):
        kwargs = {**COMMON, field: ""}
        with pytest.raises(ValidationError):
            SessionStartedEvent(**kwargs)

    @pytest.mark.parametrize("field", ["project_id", "session_id", "trace_id", "span_id", "agent_name"])
    def test_whitespace_only_raises(self, field):
        kwargs = {**COMMON, field: "   "}
        with pytest.raises(ValidationError):
            SessionStartedEvent(**kwargs)

    def test_invalid_framework_raises(self):
        with pytest.raises(ValidationError):
            SessionStartedEvent(**{**COMMON, "framework": "not-a-framework"})


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


class TestSerialisation:
    def test_to_dict_returns_json_serialisable_dict(self):
        e = SessionStartedEvent(**COMMON)
        d = e.to_dict()
        assert isinstance(d, dict)
        # Must be fully JSON-serialisable
        json.dumps(d)

    def test_to_dict_timestamp_is_string(self):
        e = SessionStartedEvent(**COMMON)
        d = e.to_dict()
        assert isinstance(d["timestamp"], str)

    def test_to_dict_enum_values_are_strings(self):
        e = SessionStartedEvent(**COMMON)
        d = e.to_dict()
        assert d["event_type"] == "session.started"
        assert d["framework"] == "langgraph"

    def test_to_json_returns_valid_json_string(self):
        e = LLMStartedEvent(**COMMON, model="gpt-4o", provider="openai")
        raw = e.to_json()
        parsed = json.loads(raw)
        assert parsed["event_type"] == "llm.started"

    def test_from_dict_roundtrip(self):
        original = SessionStartedEvent(**COMMON, input="Hello")
        restored = SessionStartedEvent.from_dict(original.to_dict())
        assert restored.event_id == original.event_id
        assert restored.input == "Hello"

    def test_from_json_roundtrip(self):
        original = LLMCompletedEvent(
            **COMMON,
            model="gpt-4o",
            provider="openai",
            output="Paris",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )
        restored = LLMCompletedEvent.from_json(original.to_json())
        assert restored.total_tokens == 15
        assert restored.output == "Paris"


# ---------------------------------------------------------------------------
# Session events
# ---------------------------------------------------------------------------


class TestSessionEvents:
    def test_started_event_type(self):
        e = SessionStartedEvent(**COMMON)
        assert e.event_type == EventType.SESSION_STARTED

    def test_started_optional_input(self):
        e = SessionStartedEvent(**COMMON, input="What is the weather?")
        assert e.input == "What is the weather?"

    def test_started_tags(self):
        e = SessionStartedEvent(**COMMON, tags=["production", "v2"])
        assert "production" in e.tags

    def test_finished_event_type(self):
        e = SessionFinishedEvent(**COMMON)
        assert e.event_type == EventType.SESSION_FINISHED

    def test_finished_success_defaults_true(self):
        e = SessionFinishedEvent(**COMMON)
        assert e.success is True

    def test_finished_with_cost(self):
        e = SessionFinishedEvent(**COMMON, total_tokens=500, total_cost_usd=0.002)
        assert e.total_tokens == 500
        assert e.total_cost_usd == pytest.approx(0.002)

    def test_finished_negative_duration_raises(self):
        with pytest.raises(ValidationError):
            SessionFinishedEvent(**COMMON, duration_ms=-1.0)


# ---------------------------------------------------------------------------
# LLM events
# ---------------------------------------------------------------------------


class TestLLMEvents:
    def test_started_event_type(self):
        e = LLMStartedEvent(**COMMON, model="gpt-4o", provider="openai")
        assert e.event_type == EventType.LLM_STARTED

    def test_started_messages(self):
        msgs = [{"role": "user", "content": "Hello"}]
        e = LLMStartedEvent(**COMMON, model="gpt-4o", provider="openai", messages=msgs)
        assert e.messages[0]["role"] == "user"

    def test_started_temperature_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            LLMStartedEvent(**COMMON, model="gpt-4o", provider="openai", temperature=3.0)

    def test_completed_event_type(self):
        e = LLMCompletedEvent(**COMMON, model="gpt-4o", provider="openai")
        assert e.event_type == EventType.LLM_COMPLETED

    def test_completed_token_counts(self):
        e = LLMCompletedEvent(
            **COMMON,
            model="gpt-4o",
            provider="openai",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        assert e.total_tokens == 150

    def test_completed_negative_tokens_raise(self):
        with pytest.raises(ValidationError):
            LLMCompletedEvent(**COMMON, model="gpt-4o", provider="openai", prompt_tokens=-1)


# ---------------------------------------------------------------------------
# Tool events
# ---------------------------------------------------------------------------


class TestToolEvents:
    CALL_ID = "call-001"

    def test_called_event_type(self):
        e = ToolCalledEvent(**COMMON, tool_name="search", call_id=self.CALL_ID)
        assert e.event_type == EventType.TOOL_CALLED

    def test_called_stores_input(self):
        e = ToolCalledEvent(**COMMON, tool_name="search", call_id=self.CALL_ID, tool_input={"query": "Paris"})
        assert e.tool_input["query"] == "Paris"

    def test_completed_event_type(self):
        e = ToolCompletedEvent(**COMMON, tool_name="search", call_id=self.CALL_ID, tool_output="result")
        assert e.event_type == EventType.TOOL_COMPLETED

    def test_failed_event_type(self):
        e = ToolFailedEvent(
            **COMMON,
            tool_name="search",
            call_id=self.CALL_ID,
            error_type="TimeoutError",
            error_message="Search timed out after 5 seconds",
        )
        assert e.event_type == EventType.TOOL_FAILED
        assert e.error_type == "TimeoutError"


# ---------------------------------------------------------------------------
# TTS events
# ---------------------------------------------------------------------------


class TestTTSEvents:
    def test_started_event_type(self):
        e = TTSStartedEvent(**COMMON, provider="elevenlabs", text="Hello, world!")
        assert e.event_type == EventType.TTS_STARTED

    def test_completed_character_count(self):
        e = TTSCompletedEvent(**COMMON, provider="elevenlabs", characters=13)
        assert e.characters == 13

    def test_completed_negative_cost_raises(self):
        with pytest.raises(ValidationError):
            TTSCompletedEvent(**COMMON, provider="elevenlabs", cost_usd=-0.01)


# ---------------------------------------------------------------------------
# STT events
# ---------------------------------------------------------------------------


class TestSTTEvents:
    def test_started_event_type(self):
        e = STTStartedEvent(**COMMON, provider="deepgram")
        assert e.event_type == EventType.STT_STARTED

    def test_completed_confidence_out_of_range_raises(self):
        with pytest.raises(ValidationError):
            STTCompletedEvent(**COMMON, provider="deepgram", confidence=1.5)

    def test_completed_transcript(self):
        e = STTCompletedEvent(**COMMON, provider="deepgram", transcript="Hello world")
        assert e.transcript == "Hello world"


# ---------------------------------------------------------------------------
# Memory events
# ---------------------------------------------------------------------------


class TestMemoryEvents:
    def test_read_event_type(self):
        e = MemoryReadEvent(**COMMON, memory_key="user_preferences")
        assert e.event_type == EventType.MEMORY_READ

    def test_write_event_type(self):
        e = MemoryWriteEvent(**COMMON, memory_key="user_preferences", value={"theme": "dark"})
        assert e.event_type == EventType.MEMORY_WRITE

    def test_memory_type_default(self):
        e = MemoryReadEvent(**COMMON, memory_key="k")
        assert e.memory_type == "short_term"


# ---------------------------------------------------------------------------
# Context events
# ---------------------------------------------------------------------------


class TestContextEvents:
    def test_loaded_event_type(self):
        e = ContextLoadedEvent(**COMMON, context_type="document", source="policy.pdf")
        assert e.event_type == EventType.CONTEXT_LOADED

    def test_truncated_defaults_false(self):
        e = ContextLoadedEvent(**COMMON, context_type="document", source="policy.pdf")
        assert e.truncated is False

    def test_negative_token_count_raises(self):
        with pytest.raises(ValidationError):
            ContextLoadedEvent(**COMMON, context_type="document", source="policy.pdf", token_count=-1)


# ---------------------------------------------------------------------------
# Error events
# ---------------------------------------------------------------------------


class TestErrorEvent:
    def test_event_type(self):
        e = ErrorEvent(**COMMON, error_type="ValueError", error_message="Bad input")
        assert e.event_type == EventType.ERROR

    def test_recoverable_defaults_false(self):
        e = ErrorEvent(**COMMON, error_type="ValueError", error_message="Bad input")
        assert e.recoverable is False

    def test_with_stack_trace(self):
        e = ErrorEvent(
            **COMMON,
            error_type="RuntimeError",
            error_message="Unexpected failure",
            stack_trace="Traceback...",
            source_event_type="llm.started",
            source_event_id="evt-999",
        )
        assert e.source_event_id == "evt-999"
        assert e.stack_trace == "Traceback..."
