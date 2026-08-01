"""LLM lifecycle events."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from contineo.events.base import BaseEvent, EventType


class LLMStartedEvent(BaseEvent):
    """Emitted immediately before an LLM API call is made.

    Attributes:
        event_type:   Always ``EventType.LLM_STARTED``.
        model:        Model identifier (e.g. ``gpt-4o``, ``claude-3-5-sonnet``).
        provider:     LLM provider name (e.g. ``openai``, ``anthropic``).
        messages:     The list of messages sent to the model.
        temperature:  Sampling temperature, if set.
        max_tokens:   Maximum tokens requested, if set.
    """

    event_type: EventType = Field(
        default=EventType.LLM_STARTED,
        frozen=True,
        description="Discriminator — always llm.started",
    )
    model: str = Field(description="Model identifier")
    provider: str = Field(description="LLM provider name")
    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Messages sent to the model",
    )
    temperature: float | None = Field(
        default=None,
        ge=0,
        le=2,
        description="Sampling temperature",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum tokens requested",
    )


class LLMCompletedEvent(BaseEvent):
    """Emitted after a successful LLM API response is received.

    Attributes:
        event_type:        Always ``EventType.LLM_COMPLETED``.
        model:             Model identifier that produced the response.
        provider:          LLM provider name.
        output:            The raw text output from the model.
        prompt_tokens:     Number of tokens in the prompt.
        completion_tokens: Number of tokens in the completion.
        total_tokens:      Total tokens consumed (prompt + completion).
        duration_ms:       Time from request to first token or full response.
        cost_usd:          Estimated USD cost for this call (optional).
        finish_reason:     Why the model stopped: ``stop``, ``length``, etc.
        tool_calls:        Any tool calls returned by the model (optional).
    """

    event_type: EventType = Field(
        default=EventType.LLM_COMPLETED,
        frozen=True,
        description="Discriminator — always llm.completed",
    )
    model: str = Field(description="Model identifier")
    provider: str = Field(description="LLM provider name")
    output: str | None = Field(default=None, description="Raw text output from the model")
    prompt_tokens: int | None = Field(default=None, ge=0, description="Prompt token count")
    completion_tokens: int | None = Field(default=None, ge=0, description="Completion token count")
    total_tokens: int | None = Field(default=None, ge=0, description="Total tokens consumed")
    duration_ms: float | None = Field(default=None, ge=0, description="Request duration in ms")
    cost_usd: float | None = Field(default=None, ge=0, description="Estimated USD cost")
    finish_reason: str | None = Field(
        default=None,
        description="Why the model stopped: stop | length | tool_calls | content_filter",
    )
    tool_calls: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Tool calls returned by the model",
    )
