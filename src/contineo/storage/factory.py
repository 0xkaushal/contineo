"""
Contineo Observe — Storage factory.

connect(url) inspects the URL scheme and returns the correct backend.
This is the recommended entry point when the user supplies a connection string.

Supported schemes:
    sqlite:///path/to/file.db   →  SqliteStorage
    sqlite:///:memory:          →  SqliteStorage (in-memory)
    postgresql://...            →  PostgresStorage
    postgres://...              →  PostgresStorage (alias)

Usage::

    import contineo
    from contineo.storage import connect

    # SQLite — local file, no extra deps
    storage = await connect("sqlite:///./contineo.db")

    # PostgreSQL — remote, requires pip install "contineo[postgres]"
    storage = await connect("postgresql://user:pass@host:5432/mydb")

    contineo.init(project_id="my-app", storage=storage)
"""

from __future__ import annotations

from urllib.parse import urlparse


async def connect(url: str):
    """Connect to a storage backend from a URL string.

    Args:
        url: A database connection URL. Scheme determines the backend:
             - ``sqlite:///path`` or ``sqlite:///:memory:`` → SqliteStorage
             - ``postgresql://...`` or ``postgres://...``  → PostgresStorage

    Returns:
        A ready-to-use StorageBackend instance.

    Raises:
        ValueError: If the URL scheme is not recognised.
        ImportError: If the required driver is not installed
                     (e.g. asyncpg for PostgreSQL).

    Examples::

        # SQLite local file
        storage = await connect("sqlite:///./contineo.db")

        # SQLite in-memory (testing)
        storage = await connect("sqlite:///:memory:")

        # PostgreSQL
        storage = await connect("postgresql://user:pass@localhost:5432/mydb")

        # Then wire into Contineo
        contineo.init(project_id="my-app", storage=storage)
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme == "sqlite":
        from contineo.storage.sqlite import SqliteStorage
        # sqlite:///:memory:   → path = ":memory:"
        # sqlite:///./file.db  → path = "./file.db"
        # sqlite:////abs/path  → path = "/abs/path"
        raw = url[len("sqlite:///"):]  # strip scheme + triple slash
        path = raw if raw else ":memory:"
        return SqliteStorage(path=path)

    if scheme in ("postgresql", "postgres"):
        from contineo.storage.postgres import PostgresStorage
        # Normalise postgres:// → postgresql:// for asyncpg
        normalised = url.replace("postgres://", "postgresql://", 1)
        return await PostgresStorage.create(normalised)

    raise ValueError(
        f"Unsupported storage URL scheme '{scheme}'. "
        f"Supported: sqlite://, postgresql://, postgres://"
    )
