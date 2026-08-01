"""
Contineo Observe — SDK package.

Re-exports the three public entry points so callers can write:

    import contineo
    contineo.init(...)
    contineo.observe(...)
    contineo.get_timeline(...)
    contineo.last_session_id()
"""

from contineo.sdk.init import init
from contineo.sdk.decorator import observe
from contineo.sdk.timeline import get_timeline, last_session_id

__all__ = [
    "init",
    "observe",
    "get_timeline",
    "last_session_id",
]
