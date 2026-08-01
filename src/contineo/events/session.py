"""Session lifecycle events."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from contineo.events.base import BaseEvent, EventType


class SessionStartedEvent(BaseEvent):
    """Emitted when an agent session begins.

    Attributes:
        event_type: Always ``EventType.SESSION_STARTED``.
        input:      The initial user input or trigger payload that started
                    the session (optional — may be absent for scheduled runs).
        tags:       Arbitrary labels for filtering sessions in the dashboard.
    """

    event_type: EventType = Field(
        default=EventType.SESSION_STARTED,
        frozen=True,
        description="Discriminator — always session.started",
    )
    input: str | None = Field(
        default=None,
        description="Initial user input or trigger payload",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Arbitrary labels for filtering / grouping sessions",
    )


class SessionFinishedEvent(BaseEvent):
    """Emitted when an agent session ends (success or failure).

    Attributes:
        event_type:        Always ``EventType.SESSION_FINISHED``.
        output:            Final output produced by the agent (optional).
        duration_ms:       Wall-clock duration of the entire session in ms.
        success:           Whether the session completed without a fatal error.
        error_message:     Human-readable error description if ``success`` is
                           False.
        total_tokens:      Aggregate token count across all LLM calls in the
                           session (optional — populated by Cost service).
        total_cost_usd:    Aggregate USD cost across all LLM calls (optional).
    """

    event_type: EventType = Field(
        default=EventType.SESSION_FINISHED,
        frozen=True,
        description="Discriminator — always session.finished",
    )
    output: str | None = Field(
        default=None,
        description="Final output produced by the agent",
    )
    duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Wall-clock session duration in milliseconds",
    )
    success: bool = Field(
        default=True,
        description="True if the session completed without a fatal error",
    )
    error_message: str | None = Field(
        default=None,
        description="Human-readable error description when success=False",
    )
    total_tokens: int | None = Field(
        default=None,
        ge=0,
        description="Aggregate token count across all LLM calls",
    )
    total_cost_usd: float | None = Field(
        default=None,
        ge=0,
        description="Aggregate USD cost across all LLM calls",
    )
