"""
Contineo Observe — Storage abstraction.

Defines the StorageBackend protocol that every storage implementation
must satisfy. The SDK depends only on this interface — never on a
specific database.

Built-in implementations:
    InMemoryStorage   — default, zero setup, data lost on process exit
    SqliteStorage     — local file, zero infra, survives restarts

Custom implementations:
    Implement StorageBackend and pass to contineo.init(storage=...)
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from contineo.timeline.models import Timeline, TimelineEntry


@runtime_checkable
class StorageBackend(Protocol):
    """Abstract interface every storage backend must implement.

    All methods are async so implementations can use async DB drivers
    without blocking the event loop.
    """

    async def save_session(self, timeline: Timeline) -> None:
        """Persist or update the top-level session record.

        Called when session.finished is received — at that point
        the Timeline has is_complete=True and total_ms set.

        Args:
            timeline: The completed (or failed) session timeline.
        """
        ...

    async def save_span(self, span: TimelineEntry) -> None:
        """Persist a single closed span.

        Called every time a span transitions from in_progress to
        completed or failed.

        Args:
            span: The closed TimelineEntry to persist.
        """
        ...

    async def get_timeline(self, session_id: str) -> Timeline | None:
        """Load a full timeline for a session from storage.

        Args:
            session_id: The session identifier.

        Returns:
            A Timeline with all its entries, or None if not found.
        """
        ...

    async def list_sessions(
        self,
        project_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Timeline]:
        """Return a paginated list of sessions for a project.

        Sessions are returned most-recent first.

        Args:
            project_id: Filter to this project.
            limit:      Maximum number of sessions to return.
            offset:     Number of sessions to skip (for pagination).

        Returns:
            List of Timeline objects (entries may be empty for list views).
        """
        ...

    async def close(self) -> None:
        """Release any connections or file handles held by this backend."""
        ...
