"""
Tests for the @contineo.observe decorator.

Covers the bug reported in FINDINGS.md [4147262d]:
  TypeError when decorating a function that does not accept a `config` kwarg.
"""

from __future__ import annotations

import asyncio

import pytest

import contineo
from contineo.sdk.state import state as _sdk_state


@pytest.fixture(autouse=True)
def fresh_init():
    """Re-initialise Contineo before every test so state is clean."""
    contineo.init(project_id="test-project")
    yield


# ---------------------------------------------------------------------------
# Bug regression: function with NO config parameter
# ---------------------------------------------------------------------------

class TestObserveNoConfigParam:
    def test_sync_function_without_config_does_not_raise(self):
        """Core bug from FINDINGS.md — must not raise TypeError."""
        @contineo.observe(agent_name="plain-agent")
        def run(question: str) -> str:
            return f"answer to: {question}"

        # Must not raise TypeError: run() got an unexpected keyword argument 'config'
        result = run("What is the weather?")
        assert result == "answer to: What is the weather?"

    @pytest.mark.asyncio
    async def test_async_function_without_config_does_not_raise(self):
        """Async path of the same bug."""
        @contineo.observe(agent_name="plain-async-agent")
        async def run(question: str) -> str:
            return f"async answer to: {question}"

        result = await run("What is the weather?")
        assert result == "async answer to: What is the weather?"

    def test_session_is_recorded_even_without_config_param(self):
        """Timeline must still capture the session even when config is not injected."""
        @contineo.observe(agent_name="plain-agent")
        def run(question: str) -> str:
            return "ok"

        run("hello")

        sid      = contineo.last_session_id()
        timeline = contineo.get_timeline(sid)

        assert timeline is not None
        assert timeline.is_complete is True
        session_entry = next(
            (e for e in timeline.entries if e.kind.value == "session"), None
        )
        assert session_entry is not None
        assert session_entry.metadata["agent_name"] == "plain-agent"


# ---------------------------------------------------------------------------
# Function WITH config param — config should still be injected
# ---------------------------------------------------------------------------

class TestObserveWithConfigParam:
    def test_function_with_config_receives_injected_callbacks(self):
        """When the function accepts config, the handler must be injected."""
        received_config = {}

        @contineo.observe(agent_name="config-agent")
        def run(question: str, config: dict | None = None) -> str:
            received_config.update(config or {})
            return "ok"

        run("hello")

        assert "callbacks" in received_config
        assert len(received_config["callbacks"]) == 1

    def test_function_with_kwargs_receives_injected_callbacks(self):
        """**kwargs functions should also receive the injected config."""
        received_kwargs = {}

        @contineo.observe(agent_name="kwargs-agent")
        def run(question: str, **kwargs) -> str:
            received_kwargs.update(kwargs)
            return "ok"

        run("hello")

        assert "config" in received_kwargs
        assert "callbacks" in received_kwargs["config"]

    def test_existing_callbacks_are_preserved(self):
        """Contineo must append to, not replace, existing callbacks."""
        sentinel = object()
        received_config = {}

        @contineo.observe(agent_name="config-agent")
        def run(question: str, config: dict | None = None) -> str:
            received_config.update(config or {})
            return "ok"

        run("hello", config={"callbacks": [sentinel]})

        callbacks = received_config.get("callbacks", [])
        assert sentinel in callbacks          # original preserved
        assert len(callbacks) == 2            # contineo handler appended


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestObserveErrorHandling:
    def test_exception_is_re_raised(self):
        @contineo.observe(agent_name="failing-agent")
        def run(question: str) -> str:
            raise ValueError("something went wrong")

        with pytest.raises(ValueError, match="something went wrong"):
            run("hello")

    def test_failed_session_is_recorded(self):
        @contineo.observe(agent_name="failing-agent")
        def run(question: str) -> str:
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            run("hello")

        timeline = contineo.get_timeline(contineo.last_session_id())
        assert timeline is not None
        session_entry = next(
            (e for e in timeline.entries if e.kind.value == "session"), None
        )
        assert session_entry is not None
        assert session_entry.status.value == "failed"
        assert session_entry.error == "boom"


# ---------------------------------------------------------------------------
# init() guard
# ---------------------------------------------------------------------------

class TestInitGuard:
    def test_observe_without_init_raises(self, monkeypatch):
        monkeypatch.setattr(_sdk_state, "initialised", False)

        @contineo.observe(agent_name="test")
        def run(q: str) -> str:
            return q

        with pytest.raises(RuntimeError, match="not initialised"):
            run("hello")


# ---------------------------------------------------------------------------
# Partial fix regression: config forwarding enables LLM/tool span recording
# FINDINGS.md [f463dc09] — only session span recorded when config not forwarded
# ---------------------------------------------------------------------------

class TestConfigForwarding:
    def test_no_config_forwarding_records_only_session_span(self):
        """When config is NOT forwarded, only the session span is recorded.
        This documents the known limitation — not a crash, but incomplete data."""

        captured_config = {}

        @contineo.observe(agent_name="no-forward-agent")
        def run(question: str) -> str:
            # simulate app.invoke without forwarding config
            return "answer"

        run("hello")

        tl = contineo.get_timeline(contineo.last_session_id())
        assert tl is not None
        # Only the session span — no LLM or tool spans because
        # the handler was never passed to any framework invoke call
        kinds = {e.kind.value for e in tl.entries}
        assert "session" in kinds
        assert "llm" not in kinds
        assert "tool" not in kinds

    def test_config_forwarding_allows_handler_to_be_injected(self):
        """When the function accepts **kwargs and forwards config,
        the callback handler is injected and available to the framework."""

        received_callbacks = []

        @contineo.observe(agent_name="forward-agent")
        def run(question: str, **kwargs) -> str:
            # Simulate what app.invoke does — pull callbacks from config
            config = kwargs.get("config") or {}
            callbacks = config.get("callbacks", [])
            received_callbacks.extend(callbacks)
            return "answer"

        run("hello")

        # The Contineo callback handler must have been injected
        assert len(received_callbacks) == 1
        from contineo.integrations.langgraph.callback import ContineoCallbackHandler
        assert isinstance(received_callbacks[0], ContineoCallbackHandler)

    def test_config_forwarding_with_explicit_config_param(self):
        """Explicit config= parameter works identically to **kwargs."""

        received_callbacks = []

        @contineo.observe(agent_name="explicit-config-agent")
        def run(question: str, config: dict | None = None) -> str:
            callbacks = (config or {}).get("callbacks", [])
            received_callbacks.extend(callbacks)
            return "answer"

        run("hello")

        assert len(received_callbacks) == 1
