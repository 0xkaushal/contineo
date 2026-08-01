"""Tool lifecycle events."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from contineo.events.base import BaseEvent, EventType


class ToolCalledEvent(BaseEvent):
    """Emitted when the agent invokes a tool.

    Attributes:
        event_type:  Always ``EventType.TOOL_CALLED``.
        tool_name:   Name of the tool being called.
        tool_input:  Arguments passed to the tool.
        call_id:     Unique identifier for this specific tool invocation,
                     used to correlate with the corresponding completed/failed
                     event.
    """

    event_type: EventType = Field(
        default=EventType.TOOL_CALLED,
        frozen=True,
        description="Discriminator — always tool.called",
    )
    tool_name: str = Field(description="Name of the tool being called")
    tool_input: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments passed to the tool",
    )
    call_id: str = Field(
        description="Unique identifier for this tool invocation (correlates with completed/failed)",
    )


class ToolCompletedEvent(BaseEvent):
    """Emitted when a tool call returns successfully.

    Attributes:
        event_type:  Always ``EventType.TOOL_COMPLETED``.
        tool_name:   Name of the tool that was called.
        call_id:     Matches the ``call_id`` on the originating
                     ``ToolCalledEvent``.
        tool_output: The return value produced by the tool.
        duration_ms: Time from call to completion in milliseconds.
    """

    event_type: EventType = Field(
        default=EventType.TOOL_COMPLETED,
        frozen=True,
        description="Discriminator — always tool.completed",
    )
    tool_name: str = Field(description="Name of the tool that was called")
    call_id: str = Field(description="Matches call_id from the originating ToolCalledEvent")
    tool_output: Any = Field(default=None, description="Return value produced by the tool")
    duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Time from call to completion in milliseconds",
    )


class ToolFailedEvent(BaseEvent):
    """Emitted when a tool call raises an exception or returns an error.

    Attributes:
        event_type:     Always ``EventType.TOOL_FAILED``.
        tool_name:      Name of the tool that failed.
        call_id:        Matches the ``call_id`` on the originating
                        ``ToolCalledEvent``.
        error_type:     Exception class name (e.g. ``ValueError``).
        error_message:  Human-readable error description.
        duration_ms:    Time from call to failure in milliseconds.
    """

    event_type: EventType = Field(
        default=EventType.TOOL_FAILED,
        frozen=True,
        description="Discriminator — always tool.failed",
    )
    tool_name: str = Field(description="Name of the tool that failed")
    call_id: str = Field(description="Matches call_id from the originating ToolCalledEvent")
    error_type: str = Field(description="Exception class name")
    error_message: str = Field(description="Human-readable error description")
    duration_ms: float | None = Field(
        default=None,
        ge=0,
        description="Time from call to failure in milliseconds",
    )
