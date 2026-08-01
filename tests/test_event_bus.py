"""Unit tests for the Contineo Observe Event Bus."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from contineo.bus.event_bus import EventBus
from contineo.bus.flags import FeatureFlags
from contineo.events.base import EventType, Framework
from contineo.events.llm import LLMCompletedEvent, LLMStartedEvent
from contineo.events.session import SessionFinishedEvent, SessionStartedEvent
from contineo.events.tool import ToolCalledEvent

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

COMMON = dict(
    project_id="proj-001",
    session_id="sess-abc",
    trace_id="trace-xyz",
    span_id="span-1",
    agent_name="test-agent",
    framework=Framework.LANGGRAPH,
)


def make_session_started(**kwargs) -> SessionStartedEvent:
    return SessionStartedEvent(**{**COMMON, **kwargs})


def make_llm_started(**kwargs) -> LLMStartedEvent:
    return LLMStartedEvent(**{**COMMON, "model": "gpt-4o", "provider": "openai", **kwargs})


def make_llm_completed(**kwargs) -> LLMCompletedEvent:
    return LLMCompletedEvent(**{**COMMON, "model": "gpt-4o", "provider": "openai", **kwargs})


# ---------------------------------------------------------------------------
# subscribe / unsubscribe
# ---------------------------------------------------------------------------


class TestSubscribe:
    def test_subscribe_returns_subscription_id(self):
        bus = EventBus()
        sid = bus.subscribe(EventType.SESSION_STARTED, lambda e: None)
        assert isinstance(sid, str) and len(sid) > 0

    def test_subscribe_all_returns_subscription_id(self):
        bus = EventBus()
        sid = bus.subscribe_all(lambda e: None)
        assert isinstance(sid, str) and len(sid) > 0

    def test_subscriber_count_increments(self):
        bus = EventBus()
        assert bus.subscriber_count == 0
        bus.subscribe(EventType.LLM_STARTED, lambda e: None)
        assert bus.subscriber_count == 1
        bus.subscribe_all(lambda e: None)
        assert bus.subscriber_count == 2

    def test_unsubscribe_returns_true_on_success(self):
        bus = EventBus()
        sid = bus.subscribe(EventType.SESSION_STARTED, lambda e: None)
        assert bus.unsubscribe(sid) is True

    def test_unsubscribe_returns_false_for_unknown_id(self):
        bus = EventBus()
        assert bus.unsubscribe("does-not-exist") is False

    def test_unsubscribe_reduces_count(self):
        bus = EventBus()
        sid = bus.subscribe(EventType.SESSION_STARTED, lambda e: None)
        bus.unsubscribe(sid)
        assert bus.subscriber_count == 0

    def test_unsubscribe_wildcard(self):
        bus = EventBus()
        sid = bus.subscribe_all(lambda e: None)
        bus.unsubscribe(sid)
        assert bus.subscriber_count == 0

    def test_subscriber_count_for_typed(self):
        bus = EventBus()
        bus.subscribe(EventType.LLM_STARTED, lambda e: None)
        bus.subscribe(EventType.LLM_STARTED, lambda e: None)
        assert bus.subscriber_count_for(EventType.LLM_STARTED) == 2
        assert bus.subscriber_count_for(EventType.SESSION_STARTED) == 0

    def test_subscriber_count_for_includes_wildcards(self):
        bus = EventBus()
        bus.subscribe(EventType.LLM_STARTED, lambda e: None)
        bus.subscribe_all(lambda e: None)
        # LLM_STARTED typed (1) + wildcard (1) = 2
        assert bus.subscriber_count_for(EventType.LLM_STARTED) == 2


# ---------------------------------------------------------------------------
# publish — sync handlers
# ---------------------------------------------------------------------------


class TestPublishSync:
    @pytest.mark.asyncio
    async def test_sync_handler_is_called(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.SESSION_STARTED, lambda e: received.append(e))
        event = make_session_started()
        await bus.publish(event)
        assert len(received) == 1
        assert received[0].event_id == event.event_id

    @pytest.mark.asyncio
    async def test_typed_handler_only_receives_matching_type(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.LLM_STARTED, lambda e: received.append(e))
        await bus.publish(make_session_started())   # should NOT trigger
        await bus.publish(make_llm_started())        # should trigger
        assert len(received) == 1
        assert received[0].event_type == EventType.LLM_STARTED

    @pytest.mark.asyncio
    async def test_wildcard_receives_all_event_types(self):
        bus = EventBus()
        received = []
        bus.subscribe_all(lambda e: received.append(e.event_type))
        await bus.publish(make_session_started())
        await bus.publish(make_llm_started())
        assert EventType.SESSION_STARTED in received
        assert EventType.LLM_STARTED in received

    @pytest.mark.asyncio
    async def test_multiple_handlers_all_called(self):
        bus = EventBus()
        calls: list[str] = []
        bus.subscribe(EventType.SESSION_STARTED, lambda e: calls.append("h1"))
        bus.subscribe(EventType.SESSION_STARTED, lambda e: calls.append("h2"))
        await bus.publish(make_session_started())
        assert sorted(calls) == ["h1", "h2"]

    @pytest.mark.asyncio
    async def test_no_handlers_publish_completes_silently(self):
        bus = EventBus()
        # Must not raise
        await bus.publish(make_session_started())

    @pytest.mark.asyncio
    async def test_unsubscribed_handler_not_called(self):
        bus = EventBus()
        received = []
        sid = bus.subscribe(EventType.SESSION_STARTED, lambda e: received.append(e))
        bus.unsubscribe(sid)
        await bus.publish(make_session_started())
        assert received == []


# ---------------------------------------------------------------------------
# publish — async handlers
# ---------------------------------------------------------------------------


class TestPublishAsync:
    @pytest.mark.asyncio
    async def test_async_handler_is_called(self):
        bus = EventBus()
        received = []

        async def handler(event):
            received.append(event)

        bus.subscribe(EventType.LLM_COMPLETED, handler)
        event = make_llm_completed()
        await bus.publish(event)
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_mixed_sync_and_async_handlers(self):
        bus = EventBus()
        calls = []

        def sync_h(event):
            calls.append("sync")

        async def async_h(event):
            calls.append("async")

        bus.subscribe(EventType.LLM_STARTED, sync_h)
        bus.subscribe(EventType.LLM_STARTED, async_h)
        await bus.publish(make_llm_started())
        assert sorted(calls) == ["async", "sync"]


# ---------------------------------------------------------------------------
# Error isolation
# ---------------------------------------------------------------------------


class TestErrorIsolation:
    @pytest.mark.asyncio
    async def test_crashing_handler_does_not_prevent_other_handlers(self):
        bus = EventBus()
        received = []

        def bad_handler(event):
            raise RuntimeError("I crashed!")

        def good_handler(event):
            received.append(event)

        bus.subscribe(EventType.SESSION_STARTED, bad_handler)
        bus.subscribe(EventType.SESSION_STARTED, good_handler)

        # Must NOT raise despite bad_handler crashing
        await bus.publish(make_session_started())
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_crashing_async_handler_does_not_prevent_other_handlers(self):
        bus = EventBus()
        received = []

        async def bad_handler(event):
            raise ValueError("async crash!")

        async def good_handler(event):
            received.append(event)

        bus.subscribe(EventType.LLM_STARTED, bad_handler)
        bus.subscribe(EventType.LLM_STARTED, good_handler)

        await bus.publish(make_llm_started())
        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_error_is_logged(self, caplog):
        import logging

        bus = EventBus()

        def bad_handler(event):
            raise RuntimeError("logged error")

        bus.subscribe(EventType.SESSION_STARTED, bad_handler)

        with caplog.at_level(logging.ERROR, logger="contineo.bus"):
            await bus.publish(make_session_started())

        assert any("Handler raised an exception" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------


class TestFeatureFlags:
    def test_all_flags_default_true(self):
        flags = FeatureFlags()
        assert flags.timeline is True
        assert flags.replay is True
        assert flags.analytics is True
        assert flags.cost is True
        assert flags.bus_logging is True

    def test_flag_disabled_via_env(self, monkeypatch):
        monkeypatch.setenv("CONTINEO_ENABLE_TIMELINE", "false")
        flags = FeatureFlags.load()
        assert flags.timeline is False

    def test_flag_enabled_via_1(self, monkeypatch):
        monkeypatch.setenv("CONTINEO_ENABLE_REPLAY", "1")
        flags = FeatureFlags.load()
        assert flags.replay is True

    def test_flag_enabled_via_yes(self, monkeypatch):
        monkeypatch.setenv("CONTINEO_ENABLE_COST", "yes")
        flags = FeatureFlags.load()
        assert flags.cost is True

    def test_flag_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("CONTINEO_ENABLE_ANALYTICS", "FALSE")
        flags = FeatureFlags.load()
        assert flags.analytics is False

    @pytest.mark.asyncio
    async def test_bus_logging_flag_suppresses_debug_logs(self, caplog):
        import logging

        flags = FeatureFlags()
        flags.bus_logging = False
        bus = EventBus(flags=flags)
        bus.subscribe(EventType.SESSION_STARTED, lambda e: None)

        with caplog.at_level(logging.DEBUG, logger="contineo.bus"):
            await bus.publish(make_session_started())

        publish_logs = [r for r in caplog.records if "Publishing event" in r.message]
        assert len(publish_logs) == 0


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_clears_all_subscriptions(self):
        bus = EventBus()
        bus.subscribe(EventType.SESSION_STARTED, lambda e: None)
        bus.subscribe_all(lambda e: None)
        assert bus.subscriber_count == 2
        await bus.shutdown()
        assert bus.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_publish_after_shutdown_is_silent(self):
        bus = EventBus()
        received = []
        bus.subscribe(EventType.SESSION_STARTED, lambda e: received.append(e))
        await bus.shutdown()
        await bus.publish(make_session_started())
        assert received == []
