"""
Contineo Observe — Storage package.
"""

from contineo.storage.interface import StorageBackend
from contineo.storage.sqlite import SqliteStorage

__all__ = [
    "StorageBackend",
    "SqliteStorage",
]
