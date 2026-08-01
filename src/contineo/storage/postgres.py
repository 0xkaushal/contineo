"""
Contineo Observe — PostgreSQL storage backend.

Connects to a remote Postgres database using asyncpg (async, production-grade).
Implements the same StorageBackend interface as SqliteStorage — the rest of
the system (TimelineService, SDK) does not know or care which backend is used.

Requires the optional 'postgres' extra:
    pip install "contineo[postgres]"

Usage::

    import contineo
    from contineo.storage import connect

    contineo.init(
        project_id="my-app",
        storage=await connect("postgresql://user:pass@host:5432/mydb"),
    )

Or directly::

    from contineo.storage import PostgresStorage

    storage = await PostgresStorage.create("postgresql://user:pass@host:5432/mydb")
    contineo.init(project_id="my-app", storage=storage)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from contineo.timeline.models import SpanKind, SpanStatus, Timeline, TimelineEntry

logger = logging.getLogger("contineo.storage.postgres")

_DDL = """
CREATE TABLE IF NOT EXISTS contineo_schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS contineo_sessions (
    session_id  TEXT        PRIMARY KEY,
    project_id  TEXT        NOT NULL DEFAULT '',
    agent_name  TEXT        NOT NULL DEFAULT '',
    framework   TEXT,
    started_at  TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    total_ms    FLOAT,
    is_complete BOOLEAN     NOT NULL DEFAULT FALSE,
    success     BOOLEAN,
    output      TEXT,
    error       TEXT,
    tags        JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contineo_spans (
    span_id     TEXT        NOT NULL,
    session_id  TEXT        NOT NULL REFERENCES contineo_sessions(session_id),
    trace_id    TEXT        NOT NULL,
    kind        TEXT        NOT NULL,
    label       TEXT        NOT NULL,
    status      TEXT        NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    duration_ms FLOAT,
    metadata    JSONB,
    error       TEXT,
    PRIMARY KEY (span_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_contineo_spans_session
    ON contineo_spans(session_id);

CREATE INDEX IF NOT EXISTS idx_contineo_sessions_project
    ON contineo_sessions(project_id, created_at DESC);
"""

_SCHEMA_VERSION = 1


class PostgresStorage:
    """Asyncpg-backed PostgreSQL storage for Contineo timelines.

    Do not construct directly — use ``PostgresStorage.create(url)``
    or the ``connect(url)`` factory which handles the async setup.

    Args:
        pool: An asyncpg connection pool.
    """

    def __init__(self, pool: Any) -> None:
        self._pool = pool

    @classmethod
    async def create(cls, url: str) -> "PostgresStorage":
        """Create a PostgresStorage with a fresh connection pool.

        Args:
            url: asyncpg-compatible connection string.
                 e.g. ``postgresql://user:pass@localhost:5432/mydb``

        Returns:
            A ready-to-use PostgresStorage instance.
        """
        try:
            import asyncpg
        except ImportError:
            raise ImportError(
                "asyncpg is required for PostgreSQL storage. "
                "Install it with: pip install \"contineo[postgres]\""
            )

        pool = await asyncpg.create_pool(url, min_size=1, max_size=5)
        instance = cls(pool)
        await instance._ensure_schema()
        logger.info(
            "PostgreSQL storage connected",
            extra={"service": "storage.postgres"},
        )
        return instance

    # ------------------------------------------------------------------
    # StorageBackend interface
    # ------------------------------------------------------------------

    async def save_session(self, timeline: Timeline) -> None:
        """Upsert the session record from a Timeline."""
        session_entry = next(
            (e for e in timeline.entries if e.kind == SpanKind.SESSION), None
        )

        project_id  = session_entry.metadata.get("project_id", "") if session_entry else ""
        agent_name  = session_entry.metadata.get("agent_name", "") if session_entry else ""
        framework   = session_entry.metadata.get("framework", "") if session_entry else ""
        started_at  = session_entry.started_at if session_entry else None
        finished_at = session_entry.finished_at if session_entry else None
        success     = None
        output      = None
        error       = None
        tags        = None

        if session_entry:
            success  = session_entry.status == SpanStatus.COMPLETED
            output   = session_entry.metadata.get("output")
            error    = session_entry.error
            tags_raw = session_entry.metadata.get("tags")
            tags     = json.dumps(tags_raw) if tags_raw else None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO contineo_sessions
                    (session_id, project_id, agent_name, framework,
                     started_at, finished_at, total_ms, is_complete,
                     success, output, error, tags)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (session_id) DO UPDATE SET
                    project_id  = EXCLUDED.project_id,
                    agent_name  = EXCLUDED.agent_name,
                    framework   = EXCLUDED.framework,
                    started_at  = EXCLUDED.started_at,
                    finished_at = EXCLUDED.finished_at,
                    total_ms    = EXCLUDED.total_ms,
                    is_complete = EXCLUDED.is_complete,
                    success     = EXCLUDED.success,
                    output      = EXCLUDED.output,
                    error       = EXCLUDED.error,
                    tags        = EXCLUDED.tags
                """,
                timeline.session_id, project_id, agent_name, framework,
                started_at, finished_at, timeline.total_ms,
                timeline.is_complete, success, output, error, tags,
            )

    async def save_span(self, span: TimelineEntry) -> None:
        """Upsert a single span."""
        async with self._pool.acquire() as conn:
            # Ensure parent session row exists
            await conn.execute(
                """
                INSERT INTO contineo_sessions (session_id, project_id, agent_name)
                VALUES ($1, '', '')
                ON CONFLICT (session_id) DO NOTHING
                """,
                span.session_id,
            )

            await conn.execute(
                """
                INSERT INTO contineo_spans
                    (span_id, session_id, trace_id, kind, label, status,
                     started_at, finished_at, duration_ms, metadata, error)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (span_id, session_id) DO UPDATE SET
                    status      = EXCLUDED.status,
                    finished_at = EXCLUDED.finished_at,
                    duration_ms = EXCLUDED.duration_ms,
                    metadata    = EXCLUDED.metadata,
                    error       = EXCLUDED.error
                """,
                span.span_id,
                span.session_id,
                span.trace_id,
                span.kind.value,
                span.label,
                span.status.value,
                span.started_at,
                span.finished_at,
                span.duration_ms,
                json.dumps(span.metadata) if span.metadata else None,
                span.error,
            )

    async def get_timeline(self, session_id: str) -> Timeline | None:
        """Load a full timeline for a session."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT session_id, is_complete, total_ms FROM contineo_sessions WHERE session_id = $1",
                session_id,
            )
            if row is None:
                return None

            span_rows = await conn.fetch(
                """
                SELECT span_id, trace_id, kind, label, status,
                       started_at, finished_at, duration_ms, metadata, error
                FROM contineo_spans
                WHERE session_id = $1
                ORDER BY started_at
                """,
                session_id,
            )

        entries = [_row_to_entry(session_id, r) for r in span_rows]
        return Timeline(
            session_id=row["session_id"],
            entries=entries,
            is_complete=row["is_complete"],
            total_ms=row["total_ms"],
        )

    async def list_sessions(
        self,
        project_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Timeline]:
        """Return most-recent sessions for a project (no spans loaded)."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT session_id, is_complete, total_ms
                FROM contineo_sessions
                WHERE project_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """,
                project_id, limit, offset,
            )

        return [
            Timeline(
                session_id=r["session_id"],
                is_complete=r["is_complete"],
                total_ms=r["total_ms"],
            )
            for r in rows
        ]

    async def close(self) -> None:
        """Close the connection pool."""
        await self._pool.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _ensure_schema(self) -> None:
        """Create tables if they do not exist."""
        async with self._pool.acquire() as conn:
            await conn.execute(_DDL)
            version = await conn.fetchval(
                "SELECT version FROM contineo_schema_version LIMIT 1"
            )
            if version is None:
                await conn.execute(
                    "INSERT INTO contineo_schema_version (version) VALUES ($1)",
                    _SCHEMA_VERSION,
                )


# ---------------------------------------------------------------------------
# Row → model helper
# ---------------------------------------------------------------------------

def _row_to_entry(session_id: str, row: Any) -> TimelineEntry:
    metadata_raw = row["metadata"]
    metadata = json.loads(metadata_raw) if isinstance(metadata_raw, str) else (metadata_raw or {})
    return TimelineEntry(
        span_id=row["span_id"],
        trace_id=row["trace_id"],
        session_id=session_id,
        kind=SpanKind(row["kind"]),
        label=row["label"],
        status=SpanStatus(row["status"]),
        started_at=_ensure_utc(row["started_at"]),
        finished_at=_ensure_utc(row["finished_at"]) if row["finished_at"] else None,
        duration_ms=row["duration_ms"],
        metadata=metadata,
        error=row["error"],
    )


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
