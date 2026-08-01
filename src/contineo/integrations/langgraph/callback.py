"""
LangGraph / LangChain adapter for Contineo Observe.

Hooks into LangChain's callback system to emit Contineo events onto the
Event Bus. Works with any LangChain or LangGraph agent — pass an instance
of ContineoCallbackHandler as a callback and all LLM calls, tool calls,
and chain runs will be tracked automatically.

Usage::

    from contineo.integrations.langgraph import ContineoCallbackHandler

    handler = ContineoCallbackHandler(
        bus=bus,
        project_id="my-project",
        session_id="sess-001",
        agent_name="weather-agent",
    )

    # Pass to any LangChain / LangGraph invoke call
    result = app.invoke(input, config={"callbacks": [handler]})
"""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from contineo.bus.event_bus import EventBus
from contineo.events.base import Framework
from contineo.events.llm import LLMCompletedEvent, LLMStartedEvent
from contineo.events.tool import ToolCalledEvent, ToolCompletedEvent, ToolFailedEvent


def _run_async(coro) -> None:
    """Fire-and-forget an async coroutine from a sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


class ContineoCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that emits Contineo Observe events.

    Attach this to any LangChain or LangGraph invocation to get automatic
    LLM and tool tracking on the Event Bus.

    Args:
        bus:        The EventBus to publish events to.
        project_id: Project identifier.
        session_id: Session identifier (one per agent run).
        agent_name: Human-readable agent name.
        trace_id:   Distributed trace ID. Auto-generated if not supplied.
        framework:  Defaults to Framework.LANGGRAPH.
    """

    def __init__(
        self,
        bus: EventBus,
        project_id: str,
        session_id: str,
        agent_name: str,
        trace_id: str | None = None,
        framework: Framework = Framework.LANGGRAPH,
    ) -> None:
        super().__init__()
        self._bus = bus
        self._project_id = project_id
        self._session_id = session_id
        self._agent_name = agent_name
        self._trace_id = trace_id or str(uuid.uuid4())
        self._framework = framework

        # run_id (UUID from LangChain) → (span_id, start_time_ms)
        self._llm_runs: dict[str, tuple[str, float]] = {}
        self._tool_runs: dict[str, tuple[str, float, str]] = {}  # run_id → (call_id, start_ms, tool_name)

    # ------------------------------------------------------------------
    # LLM callbacks
    # ------------------------------------------------------------------

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        span_id = str(uuid.uuid4())
        start_ms = time.monotonic() * 1000
        self._llm_runs[str(run_id)] = (span_id, start_ms)

        # Extract model name from serialized or kwargs
        model = (
            kwargs.get("invocation_params", {}).get("model")
            or kwargs.get("invocation_params", {}).get("model_name")
            or serialized.get("kwargs", {}).get("model_name")
            or serialized.get("kwargs", {}).get("model")
            or "unknown"
        )
        provider = _infer_provider(model, serialized)

        messages = [{"role": "user", "content": p} for p in prompts]

        event = LLMStartedEvent(
            project_id=self._project_id,
            session_id=self._session_id,
            trace_id=self._trace_id,
            span_id=span_id,
            agent_name=self._agent_name,
            framework=self._framework,
            model=model,
            provider=provider,
            messages=messages,
            temperature=kwargs.get("invocation_params", {}).get("temperature"),
        )
        _run_async(self._bus.publish(event))

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        span_id = str(uuid.uuid4())
        start_ms = time.monotonic() * 1000
        self._llm_runs[str(run_id)] = (span_id, start_ms)

        model = (
            kwargs.get("invocation_params", {}).get("model")
            or kwargs.get("invocation_params", {}).get("model_name")
            or serialized.get("kwargs", {}).get("model_name")
            or serialized.get("kwargs", {}).get("model")
            or "unknown"
        )
        provider = _infer_provider(model, serialized)

        # Flatten chat messages to dicts
        flat_messages = []
        for message_group in messages:
            for msg in message_group:
                flat_messages.append({
                    "role": getattr(msg, "type", "unknown"),
                    "content": str(msg.content)[:500],  # truncate long prompts
                })

        event = LLMStartedEvent(
            project_id=self._project_id,
            session_id=self._session_id,
            trace_id=self._trace_id,
            span_id=span_id,
            agent_name=self._agent_name,
            framework=self._framework,
            model=model,
            provider=provider,
            messages=flat_messages,
        )
        _run_async(self._bus.publish(event))

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        run_key = str(run_id)
        if run_key not in self._llm_runs:
            return

        span_id, start_ms = self._llm_runs.pop(run_key)
        duration_ms = time.monotonic() * 1000 - start_ms

        # Extract token usage from LLMResult metadata
        token_usage = {}
        if response.llm_output:
            token_usage = response.llm_output.get("token_usage", {})

        # Extract output text
        output = None
        if response.generations and response.generations[0]:
            gen = response.generations[0][0]
            output = getattr(gen, "text", None) or str(getattr(gen, "message", ""))

        # Extract model name
        model = "unknown"
        if response.llm_output:
            model = response.llm_output.get("model_name", "unknown")

        event = LLMCompletedEvent(
            project_id=self._project_id,
            session_id=self._session_id,
            trace_id=self._trace_id,
            span_id=span_id,
            agent_name=self._agent_name,
            framework=self._framework,
            model=model,
            provider=_infer_provider(model, {}),
            output=output,
            prompt_tokens=token_usage.get("prompt_tokens"),
            completion_tokens=token_usage.get("completion_tokens"),
            total_tokens=token_usage.get("total_tokens"),
            duration_ms=round(duration_ms, 2),
        )
        _run_async(self._bus.publish(event))

    def on_llm_error(self, error: Exception, *, run_id: uuid.UUID, **kwargs: Any) -> None:
        self._llm_runs.pop(str(run_id), None)

    # ------------------------------------------------------------------
    # Tool callbacks
    # ------------------------------------------------------------------

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        call_id = str(uuid.uuid4())
        start_ms = time.monotonic() * 1000
        tool_name = serialized.get("name", "unknown_tool")
        self._tool_runs[str(run_id)] = (call_id, start_ms, tool_name)

        # Try to parse the input as a dict, fall back to string
        try:
            import json
            tool_input = json.loads(input_str)
        except Exception:
            tool_input = {"input": input_str}

        event = ToolCalledEvent(
            project_id=self._project_id,
            session_id=self._session_id,
            trace_id=self._trace_id,
            span_id=str(uuid.uuid4()),
            agent_name=self._agent_name,
            framework=self._framework,
            tool_name=tool_name,
            tool_input=tool_input,
            call_id=call_id,
        )
        _run_async(self._bus.publish(event))

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        run_key = str(run_id)
        if run_key not in self._tool_runs:
            return

        call_id, start_ms, tool_name = self._tool_runs.pop(run_key)
        duration_ms = time.monotonic() * 1000 - start_ms

        event = ToolCompletedEvent(
            project_id=self._project_id,
            session_id=self._session_id,
            trace_id=self._trace_id,
            span_id=str(uuid.uuid4()),
            agent_name=self._agent_name,
            framework=self._framework,
            tool_name=tool_name,
            call_id=call_id,
            tool_output=str(output)[:1000],
            duration_ms=round(duration_ms, 2),
        )
        _run_async(self._bus.publish(event))

    def on_tool_error(
        self,
        error: Exception,
        *,
        run_id: uuid.UUID,
        **kwargs: Any,
    ) -> None:
        run_key = str(run_id)
        if run_key not in self._tool_runs:
            return

        call_id, start_ms, tool_name = self._tool_runs.pop(run_key)
        duration_ms = time.monotonic() * 1000 - start_ms

        event = ToolFailedEvent(
            project_id=self._project_id,
            session_id=self._session_id,
            trace_id=self._trace_id,
            span_id=str(uuid.uuid4()),
            agent_name=self._agent_name,
            framework=self._framework,
            tool_name=tool_name,
            call_id=call_id,
            error_type=type(error).__name__,
            error_message=str(error),
            duration_ms=round(duration_ms, 2),
        )
        _run_async(self._bus.publish(event))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_provider(model: str, serialized: dict[str, Any]) -> str:
    """Guess the LLM provider from the model name or serialized class path."""
    model_lower = model.lower()
    if "gpt" in model_lower or "openai" in model_lower:
        return "openai"
    if "claude" in model_lower or "anthropic" in model_lower:
        return "anthropic"
    if "gemini" in model_lower or "google" in model_lower:
        return "google"
    if "mistral" in model_lower:
        return "mistral"
    if "llama" in model_lower or "meta" in model_lower:
        return "meta"

    # Fall back to class path in serialized
    class_path = str(serialized.get("id", ""))
    if "openai" in class_path.lower():
        return "openai"
    if "anthropic" in class_path.lower():
        return "anthropic"

    return "unknown"
