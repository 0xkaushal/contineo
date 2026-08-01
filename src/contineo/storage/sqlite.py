"""
Contineo Observe — SQLite storage backend.

Local file-based persistence. Zero infrastructure required — just a path
to a .db file. Data survives process restarts.

Usage::

    import contineo
    from contineo.storage.sqlite import SqliteStorage

    contineo.init(
        project_id="my-app",
        storage=SqliteStorage(path="./contineo.db"),
    )

The database is created automatically on first use.
Uses Python's built-in sqlite3 module — no extra dependencies.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contineo.timeline.models import SpanKind, SpanStatus, Timeline, TimelineEntry

logger = logging.getLogger("contineo.storage.sqlite")

# Schema version — bump when making breaking schema changes
_SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT    PRIMARY KEY,
    project_id  TEXT    NOT NULL,
    agent_name  TEXT    NOT NULL,
    framework   TEXT,
    started_at  TEXT,
    finished_at TEXT,
    total_ms    REAL,
    is_complete INTEGER NOT NULL DEFAULT 0,
    success     INTEGER,
    output      TEXT,
    error       TEXT,
    tags        TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS spans (
    span_id     TEXT    NOT NULL,
    session_id  TEXT    NOT NULL REFERENCES sessions(session_id),
    trace_id    TEXT    NOT NULL,
    kind        TEXT    NOT NULL,
    label       TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    started_at  TEXT    NOT NULL,
    finished_at TEXT,
    duration_ms REAL,
    metadata    TEXT,
    error       TEXT,
    PRIMARY KEY (span_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_spans_session ON spans(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id, created_at DESC);
"""


class SqliteStorage:
    """SQLite-backed storage for Contineo timelines.

    Thread-safe via check_same_thread=False and Python's GIL.
    All methods are async for interface compatibility — internally
    uses synchronous sqlite3 (acceptable for local dev workloads).

    Args:
        path: Path to the SQLite database file.
              Use ":memory:" for a purely in-process database (testing).
    """

    def __init__(self, path: str | Path = "./contineo.db") -> None:
        self._path = str(path)
        self._conn: sqlite3.Connection | None = None
        self._ensure_connected()

    # ------------------------------------------------------------------
    # StorageBackend interface
    # ------------------------------------------------------------------

    async def save_session(self, timeline: Timeline) -> None:
        """Upsert the session record from a Timeline."""
        conn = self._ensure_connected()

        # Pull session-level metadata from the session span if present
        session_entry = next(
            (e for e in timeline.entries if e.kind == SpanKind.SESSION), None
        )
        agent_name  = session_entry.metadata.get("agent_name", "") if session_entry else ""
        framework   = session_entry.metadata.get("framework", "") if session_entry else ""
        started_at  = session_entry.started_at.isoformat() if session_entry else None
        finished_at = session_entry.finished_at.isoformat() if session_entry else None
        success     = None
        output      = None
        error       = None
        tags        = None

        if session_entry:
            success     = 1 if session_entry.status == SpanStatus.COMPLETED else 0
            output      = session_entry.metadata.get("output")
            error       = session_entry.error
            tags_raw    = session_entry.metadata.get("tags")
            tags        = json.dumps(tags_raw) if tags_raw else None

        conn.execute(
            """
            INSERT INTO sessions
                (session_id, project_id, agent_name, framework,
                 started_at, finished_at, total_ms, is_complete,
                 success, output, error, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                project_id  = excluded.project_id,
                agent_name  = excluded.agent_name,
                framework   = excluded.framework,
                started_at  = excluded.started_at,
                finished_at = excluded.finished_at,
                total_ms    = excluded.total_ms,
                is_complete = excluded.is_complete,
                success     = excluded.success,
                output      = excluded.output,
                error       = excluded.error,
                tags        = excluded.tags
            """,
            (
                timeline.session_id,
                _project_id_from(timeline),
                agent_name,
                framework,
                started_at,
                finished_at,
                timeline.total_ms,
                1 if timeline.is_complete else 0,
                success,
                output,
                error,
                tags,
            ),
        )
        conn.commit()
        logger.debug(
            "Session saved",
            extra={"session_id": timeline.session_id, "service": "storage.sqlite"},
        )

    async def save_span(self, span: TimelineEntry) -> None:
        """Upsert a single span."""
        conn = self._ensure_connected()

        # Ensure the parent session row exists (may arrive before session span)
        conn.execute(
            """
            INSERT OR IGNORE INTO sessions
                (session_id, project_id, agent_name, is_complete)
            VALUES (?, ?, ?, 0)
            """,
            (span.session_id, "", ""),
        )

        conn.execute(
            """
            INSERT INTO spans
                (span_id, session_id, trace_id, kind, label, status,
                 started_at, finished_at, duration_ms, metadata, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(span_id, session_id) DO UPDATE SET
                status      = excluded.status,
                finished_at = excluded.finished_at,
                duration_ms = excluded.duration_ms,
                metadata    = excluded.metadata,
                error       = excluded.error
            """,
            (
                span.span_id,
                span.session_id,
                span.trace_id,
                span.kind.value,
                span.label,
                span.status.value,
                span.started_at.isoformat(),
                span.finished_at.isoformat() if span.finished_at else None,
                span.duration_ms,
                json.dumps(span.metadata) if span.metadata else None,
                span.error,
            ),
        )
        conn.commit()

    async def get_timeline(self, session_id: str) -> Timeline | None:
        """Load a full timeline for a session."""
        conn = self._ensure_connected()

        row = conn.execute(
            "SELECT session_id, is_complete, total_ms FROM sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()

        if row is None:
            return None

        span_rows = conn.execute(
            """
            SELECT span_id, trace_id, kind, label, status,
                   started_at, finished_at, duration_ms, metadata, error
            FROM spans
            WHERE session_id = ?
            ORDER BY started_at
            """,
            (session_id,),
        ).fetchall()

        entries = [_row_to_entry(session_id, r) for r in span_rows]

        return Timeline(
            session_id=row[0],
            entries=entries,
            is_complete=bool(row[1]),
            total_ms=row[2],
        )

    async def list_sessions(
        self,
        project_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Timeline]:
        """Return most-recent sessions for a project (no spans loaded)."""
        conn = self._ensure_connected()

        rows = conn.execute(
            """
            SELECT session_id, is_complete, total_ms
            FROM sessions
            WHERE project_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (project_id, limit, offset),
        ).fetchall()

        return [
            Timeline(session_id=r[0], is_complete=bool(r[1]), total_ms=r[2])
            for r in rows
        ]

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_DDL)
            self._conn.commit()
            self._maybe_stamp_version()
            logger.info(
                "SQLite storage connected",
                extra={"path": self._path, "service": "storage.sqlite"},
            )
        return self._conn

    def _maybe_stamp_version(self) -> None:
        row = self._conn.execute("SELECT version FROM schema_version").fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)", (_SCHEMA_VERSION,)
            )
            self._conn.commit()


# ---------------------------------------------------------------------------
# Row → model helpers
# ---------------------------------------------------------------------------

def _row_to_entry(session_id: str, row: sqlite3.Row) -> TimelineEntry:
    metadata = json.loads(row["metadata"]) if row["metadata"] else {}
    return TimelineEntry(
        span_id=row["span_id"],
        trace_id=row["trace_id"],
        session_id=session_id,
        kind=SpanKind(row["kind"]),
        label=row["label"],
        status=SpanStatus(row["status"]),
        started_at=_parse_dt(row["started_at"]),
        finished_at=_parse_dt(row["finished_at"]) if row["finished_at"] else None,
        duration_ms=row["duration_ms"],
        metadata=metadata,
        error=row["error"],
    )


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _project_id_from(timeline: Timeline) -> str:
    """Extract project_id from the session span metadata if available."""
    session_entry = next(
        (e for e in timeline.entries if e.kind == SpanKind.SESSION), None
    )
    if session_entry:
        return session_entry.metadata.get("project_id", "")
    return ""
