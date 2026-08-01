"""Memory lifecycle events."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from contineo.events.base import BaseEvent, EventType


class MemoryReadEvent(BaseEvent):
    """Emitted when the agent reads from memory.

    Attributes:
        event_type:   Always ``EventType.MEMORY_READ``.
        memory_key:   Key or identifier of the memory entry being read.
        memory_type:  Type of memory store (e.g. ``short_term``, ``long_term``,
                      ``episodic``, ``semantic``).
        value:        The value retrieved (optional — may be omitted if large).
        duration_ms:  Time taken for the read operation.
    """

    event_type: EventType = Field(
        default=EventType.MEMORY_READ,
        frozen=True,
        description="Discriminator — always memory.read",
    )
    memory_key: str = Field(description="Key or identifier of the memory entry")
    memory_type: str = Field(
        default="short_term",
        description="Type of memory store: short_term | long_term | episodic | semantic",
    )
    value: Any = Field(default=None, description="Value retrieved from memory")
    duration_ms: float | None = Field(default=None, ge=0, description="Read duration in ms")


class MemoryWriteEvent(BaseEvent):
    """Emitted when the agent writes to memory.

    Attributes:
        event_type:   Always ``EventType.MEMORY_WRITE``.
        memory_key:   Key or identifier of the memory entry being written.
        memory_type:  Type of memory store.
        value:        The value being stored (optional — may be omitted if large).
        duration_ms:  Time taken for the write operation.
    """

    event_type: EventType = Field(
        default=EventType.MEMORY_WRITE,
        frozen=True,
        description="Discriminator — always memory.write",
    )
    memory_key: str = Field(description="Key or identifier of the memory entry")
    memory_type: str = Field(
        default="short_term",
        description="Type of memory store: short_term | long_term | episodic | semantic",
    )
    value: Any = Field(default=None, description="Value being stored in memory")
    duration_ms: float | None = Field(default=None, ge=0, description="Write duration in ms")
