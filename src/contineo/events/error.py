"""Error event — emitted whenever any exception occurs during agent execution."""

from __future__ import annotations

from pydantic import Field

from contineo.events.base import BaseEvent, EventType


class ErrorEvent(BaseEvent):
    """Emitted when an unhandled exception or fatal error occurs.

    Per architecture guidelines, no exceptions should be swallowed.
    Every exception must produce an ErrorEvent on the Event Bus.

    Attributes:
        event_type:     Always ``EventType.ERROR``.
        error_type:     Exception class name (e.g. ``ValueError``,
                        ``TimeoutError``).
        error_message:  Human-readable description of what went wrong.
        stack_trace:    Full stack trace string (optional — include in
                        development; consider omitting in production to avoid
                        leaking internals).
        source_event_type: The event type that was being processed when the
                           error occurred (optional, for correlation).
        source_event_id:   The ``event_id`` of the event being processed
                           (optional, for correlation).
        recoverable:    True if the agent can continue after this error,
                        False if the session must be terminated.
    """

    event_type: EventType = Field(
        default=EventType.ERROR,
        frozen=True,
        description="Discriminator — always error",
    )
    error_type: str = Field(description="Exception class name")
    error_message: str = Field(description="Human-readable error description")
    stack_trace: str | None = Field(
        default=None,
        description="Full stack trace (consider omitting in production)",
    )
    source_event_type: str | None = Field(
        default=None,
        description="event_type of the event being processed when the error occurred",
    )
    source_event_id: str | None = Field(
        default=None,
        description="event_id of the event being processed when the error occurred",
    )
    recoverable: bool = Field(
        default=False,
        description="True if the agent can continue; False if session must terminate",
    )
