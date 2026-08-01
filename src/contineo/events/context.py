"""Context lifecycle events."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from contineo.events.base import BaseEvent, EventType


class ContextLoadedEvent(BaseEvent):
    """Emitted when context is loaded into the agent's working memory.

    Attributes:
        event_type:     Always ``EventType.CONTEXT_LOADED``.
        context_type:   What kind of context was loaded (e.g. ``document``,
                        ``database``, ``api``, ``file``).
        source:         Human-readable identifier of the context source
                        (e.g. a file path, URL, or table name).
        token_count:    Approximate number of tokens consumed by the loaded
                        context (optional).
        duration_ms:    Time taken to load the context in milliseconds.
        truncated:      True if the context was truncated to fit the context
                        window.
    """

    event_type: EventType = Field(
        default=EventType.CONTEXT_LOADED,
        frozen=True,
        description="Discriminator — always context.loaded",
    )
    context_type: str = Field(
        description="Kind of context loaded: document | database | api | file | etc.",
    )
    source: str = Field(description="Human-readable identifier of the context source")
    token_count: int | None = Field(
        default=None,
        ge=0,
        description="Approximate tokens consumed by the loaded context",
    )
    duration_ms: float | None = Field(default=None, ge=0, description="Load duration in ms")
    truncated: bool = Field(
        default=False,
        description="True if the context was truncated to fit the context window",
    )
