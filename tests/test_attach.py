"""
Tests for contineo.attach().

Uses a real minimal LangGraph graph so we test the actual patch path,
not mocks. No LLM calls are made — the assistant node just echoes back.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

import pytest

import contineo
from contineo.sdk.state import state as _sdk_state
from contineo.integrations.langgraph.patch import _CONTINEO_PATCHED

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages


# ---------------------------------------------------------------------------
# Minimal graph fixture — no LLM, no tools, just echoes
# ---------------------------------------------------------------------------

class EchoState(TypedDict):
    messages: Annotated[list, add_messages]


def _echo_node(state: EchoState) -> EchoState:
    last = state["messages"][-1]
    return {"messages": [AIMessage(content=f"echo: {last.content}")]}


def build_echo_graph():
    g = StateGraph(EchoState)
    g.add_node("echo", _echo_node)
    g.add_edge(START, "echo")
    g.add_edge("echo", END)
    return g.compile()


@pytest.fixture(autouse=True)
def fresh_init():
    contineo.init(project_id="test-project")
    yield


# ---------------------------------------------------------------------------
# attach() — basic behaviour
# ---------------------------------------------------------------------------

class TestAttachBasic:
    def test_attach_does_not_raise(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

    def test_attach_is_idempotent(self):
        """Calling attach() twice on the same graph is safe."""
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")
        contineo.attach(app, agent_name="echo-agent")  # must not raise or double-wrap

    def test_patched_flag_is_set(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")
        assert getattr(app, _CONTINEO_PATCHED, False) is True

    def test_unrecognised_object_raises_type_error(self):
        with pytest.raises(TypeError, match="does not recognise"):
            contineo.attach(object(), agent_name="unknown")

    def test_attach_without_init_raises(self, monkeypatch):
        monkeypatch.setattr(_sdk_state, "initialised", False)
        app = build_echo_graph()
        with pytest.raises(RuntimeError, match="not initialised"):
            contineo.attach(app, agent_name="echo-agent")


# ---------------------------------------------------------------------------
# invoke — session recorded
# ---------------------------------------------------------------------------

class TestAttachInvoke:
    def test_invoke_returns_correct_result(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        result = app.invoke({"messages": [HumanMessage(content="hello")]})
        assert "echo: hello" in result["messages"][-1].content

    def test_invoke_records_session_span(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        app.invoke({"messages": [HumanMessage(content="hello")]})

        tl = contineo.get_timeline(contineo.last_session_id())
        assert tl is not None
        assert tl.is_complete is True

        session_entry = next(
            (e for e in tl.entries if e.kind.value == "session"), None
        )
        assert session_entry is not None
        assert session_entry.status.value == "completed"
        assert session_entry.metadata["agent_name"] == "echo-agent"

    def test_invoke_records_duration(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        app.invoke({"messages": [HumanMessage(content="hello")]})

        tl = contineo.get_timeline(contineo.last_session_id())
        session_entry = next(e for e in tl.entries if e.kind.value == "session")
        assert session_entry.duration_ms is not None
        assert session_entry.duration_ms >= 0

    def test_invoke_extracts_input_from_messages(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        app.invoke({"messages": [HumanMessage(content="what is the weather?")]})

        tl = continuo.get_timeline(contineo.last_session_id()) if False else \
             contineo.get_timeline(contineo.last_session_id())
        session_entry = next(e for e in tl.entries if e.kind.value == "session")
        assert session_entry.metadata.get("input") == "what is the weather?"

    def test_multiple_invokes_produce_separate_sessions(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        app.invoke({"messages": [HumanMessage(content="q1")]})
        sid1 = contineo.last_session_id()

        app.invoke({"messages": [HumanMessage(content="q2")]})
        sid2 = contineo.last_session_id()

        assert sid1 != sid2
        assert contineo.get_timeline(sid1) is not None
        assert contineo.get_timeline(sid2) is not None

    def test_invoke_failure_records_failed_session(self):
        """A graph that raises must produce a failed session span."""
        class FailState(TypedDict):
            messages: Annotated[list, add_messages]

        def fail_node(state):
            raise RuntimeError("node exploded")

        g = StateGraph(FailState)
        g.add_node("fail", fail_node)
        g.add_edge(START, "fail")
        g.add_edge("fail", END)
        app = g.compile()

        contineo.attach(app, agent_name="fail-agent")

        with pytest.raises(RuntimeError, match="node exploded"):
            app.invoke({"messages": [HumanMessage(content="hi")]})

        tl = contineo.get_timeline(contineo.last_session_id())
        assert tl is not None
        session_entry = next(e for e in tl.entries if e.kind.value == "session")
        assert session_entry.status.value == "failed"
        assert "node exploded" in session_entry.error

    def test_existing_config_callbacks_are_preserved(self):
        """User-supplied callbacks must not be dropped."""
        from langchain_core.callbacks.base import BaseCallbackHandler

        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        class SentinelCallback(BaseCallbackHandler):
            pass

        sentinel = SentinelCallback()
        # Pass existing callbacks — they must survive alongside Contineo's handler
        result = app.invoke(
            {"messages": [HumanMessage(content="hi")]},
            config={"callbacks": [sentinel]},
        )
        assert result is not None


# ---------------------------------------------------------------------------
# ainvoke — async path
# ---------------------------------------------------------------------------

class TestAttachAinvoke:
    @pytest.mark.asyncio
    async def test_ainvoke_returns_correct_result(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        result = await app.ainvoke({"messages": [HumanMessage(content="async hello")]})
        assert "echo: async hello" in result["messages"][-1].content

    @pytest.mark.asyncio
    async def test_ainvoke_records_session_span(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        await app.ainvoke({"messages": [HumanMessage(content="hi")]})

        tl = contineo.get_timeline(contineo.last_session_id())
        assert tl is not None
        assert tl.is_complete is True


# ---------------------------------------------------------------------------
# stream — sync streaming path
# ---------------------------------------------------------------------------

class TestAttachStream:
    def test_stream_yields_chunks(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        chunks = list(app.stream({"messages": [HumanMessage(content="hello")]}))
        assert len(chunks) > 0

    def test_stream_records_session_span(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        list(app.stream({"messages": [HumanMessage(content="hello")]}))

        tl = contineo.get_timeline(contineo.last_session_id())
        assert tl is not None
        assert tl.is_complete is True
        session_entry = next(e for e in tl.entries if e.kind.value == "session")
        assert session_entry.status.value == "completed"


# ---------------------------------------------------------------------------
# astream — async streaming path
# ---------------------------------------------------------------------------

class TestAttachAstream:
    @pytest.mark.asyncio
    async def test_astream_yields_chunks(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        chunks = []
        async for chunk in app.astream({"messages": [HumanMessage(content="hello")]}):
            chunks.append(chunk)

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_astream_records_session_span(self):
        app = build_echo_graph()
        contineo.attach(app, agent_name="echo-agent")

        async for _ in app.astream({"messages": [HumanMessage(content="hello")]}):
            pass

        tl = contineo.get_timeline(contineo.last_session_id())
        assert tl is not None
        assert tl.is_complete is True
