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
