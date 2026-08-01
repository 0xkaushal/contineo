"""
Tests for SqliteStorage and storage wiring.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import pytest

import contineo
from contineo.storage.sqlite import SqliteStorage
from contineo.timeline.models import SpanKind, SpanStatus, Timeline, TimelineEntry

T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_entry(**kwargs) -> TimelineEntry:
    defaults = dict(
        span_id="span-1",
        trace_id="trace-1",
        session_id="sess-1",
        kind=SpanKind.LLM,
        label="LLM: gpt-4o",
        status=SpanStatus.COMPLETED,
        started_at=T0,
        finished_at=T0,
        duration_ms=500.0,
        metadata={"model": "gpt-4o"},
    )
    defaults.update(kwargs)
    return TimelineEntry(**defaults)


def make_session_entry(**kwargs) -> TimelineEntry:
    defaults = dict(
        span_id="span-sess",
        trace_id="trace-1",
        session_id="sess-1",
        kind=SpanKind.SESSION,
        label="Session: test-agent",
        status=SpanStatus.COMPLETED,
        started_at=T0,
        finished_at=T0,
        duration_ms=1000.0,
        metadata={
            "agent_name": "test-agent",
            "framework": "langgraph",
            "project_id": "proj-1",
        },
    )
    defaults.update(kwargs)
    return TimelineEntry(**defaults)


@pytest.fixture
async def storage():
    s = SqliteStorage(path=":memory:")
    yield s
    await s.close()


# ---------------------------------------------------------------------------
# save_span / get_timeline
# ---------------------------------------------------------------------------

class TestSaveSpan:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_span(self, storage):
        entry = make_entry()
        await storage.save_span(entry)

        tl = await storage.get_timeline("sess-1")
        assert tl is not None
        assert len(tl.entries) == 1
        assert tl.entries[0].span_id == "span-1"
        assert tl.entries[0].kind == SpanKind.LLM
        assert tl.entries[0].duration_ms == 500.0

    @pytest.mark.asyncio
    async def test_span_metadata_roundtrip(self, storage):
        entry = make_entry(metadata={"model": "gpt-4o", "tokens": 150})
        await storage.save_span(entry)

        tl = await storage.get_timeline("sess-1")
        assert tl.entries[0].metadata["model"] == "gpt-4o"
        assert tl.entries[0].metadata["tokens"] == 150

    @pytest.mark.asyncio
    async def test_multiple_spans_same_session(self, storage):
        for i in range(3):
            await storage.save_span(make_entry(span_id=f"span-{i}"))

        tl = await storage.get_timeline("sess-1")
        assert len(tl.entries) == 3

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_span(self, storage):
        await storage.save_span(make_entry(status=SpanStatus.IN_PROGRESS, duration_ms=None))
        await storage.save_span(make_entry(status=SpanStatus.COMPLETED, duration_ms=800.0))

        tl = await storage.get_timeline("sess-1")
        assert len(tl.entries) == 1
        assert tl.entries[0].status == SpanStatus.COMPLETED
        assert tl.entries[0].duration_ms == 800.0

    @pytest.mark.asyncio
    async def test_get_timeline_returns_none_for_unknown_session(self, storage):
        result = await storage.get_timeline("no-such-session")
        assert result is None


# ---------------------------------------------------------------------------
# save_session
# ---------------------------------------------------------------------------

class TestSaveSession:
    @pytest.mark.asyncio
    async def test_save_and_retrieve_complete_session(self, storage):
        tl = Timeline(
            session_id="sess-1",
            entries=[make_session_entry()],
            is_complete=True,
            total_ms=1000.0,
        )
        await storage.save_session(tl)

        result = await storage.get_timeline("sess-1")
        assert result is not None
        assert result.is_complete is True
        assert result.total_ms == 1000.0

    @pytest.mark.asyncio
    async def test_session_upsert_updates_completion(self, storage):
        # Save incomplete
        await storage.save_session(
            Timeline(session_id="sess-1", entries=[], is_complete=False)
        )
        # Save completed
        await storage.save_session(
            Timeline(
                session_id="sess-1",
                entries=[make_session_entry()],
                is_complete=True,
                total_ms=1500.0,
            )
        )

        result = await storage.get_timeline("sess-1")
        assert result.is_complete is True
        assert result.total_ms == 1500.0


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------

class TestListSessions:
    @pytest.mark.asyncio
    async def test_list_sessions_for_project(self, storage):
        for i in range(3):
            entry = make_session_entry(
                session_id=f"sess-{i}",
                metadata={"agent_name": "a", "framework": "langgraph", "project_id": "proj-1"},
            )
            await storage.save_session(
                Timeline(session_id=f"sess-{i}", entries=[entry], is_complete=True)
            )

        sessions = await storage.list_sessions("proj-1")
        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_list_sessions_different_projects_isolated(self, storage):
        for proj in ("proj-a", "proj-b"):
            entry = make_session_entry(
                session_id=f"sess-{proj}",
                metadata={"agent_name": "a", "framework": "langgraph", "project_id": proj},
            )
            await storage.save_session(
                Timeline(session_id=f"sess-{proj}", entries=[entry], is_complete=True)
            )

        proj_a = await storage.list_sessions("proj-a")
        proj_b = await storage.list_sessions("proj-b")
        assert len(proj_a) == 1
        assert len(proj_b) == 1

    @pytest.mark.asyncio
    async def test_list_sessions_pagination(self, storage):
        for i in range(5):
            entry = make_session_entry(
                session_id=f"sess-{i}",
                metadata={"agent_name": "a", "framework": "langgraph", "project_id": "proj-1"},
            )
            await storage.save_session(
                Timeline(session_id=f"sess-{i}", entries=[entry], is_complete=True)
            )

        page1 = await storage.list_sessions("proj-1", limit=3, offset=0)
        page2 = await storage.list_sessions("proj-1", limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 2


# ---------------------------------------------------------------------------
# End-to-end: SDK init with SqliteStorage
# ---------------------------------------------------------------------------

class TestSDKWithStorage:
    @pytest.fixture(autouse=True)
    async def init_with_storage(self):
        storage = SqliteStorage(path=":memory:")
        contineo.init(project_id="test-project", storage=storage)
        self._storage = storage
        yield
        await storage.close()

    @pytest.mark.asyncio
    async def test_observe_persists_session_to_storage(self):
        @contineo.observe(agent_name="test-agent")
        def run(q: str) -> str:
            return "answer"

        run("hello")
        await asyncio.sleep(0.05)  # let fire() tasks settle

        sid = contineo.last_session_id()
        stored = await self._storage.get_timeline(sid)
        assert stored is not None

    @pytest.mark.asyncio
    async def test_session_survives_memory_clear(self):
        """Simulate process restart — clear memory, load from storage."""

        @contineo.observe(agent_name="test-agent")
        def run(q: str) -> str:
            return "answer"

        run("hello")
        await asyncio.sleep(0.05)

        sid = contineo.last_session_id()

        # Wipe in-memory timeline
        from contineo.sdk.state import state
        state.timeline._timelines.clear()

        # Storage fallback should reload it
        stored = await self._storage.get_timeline(sid)
        assert stored is not None
        assert stored.session_id == sid
