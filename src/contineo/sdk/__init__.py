"""
Contineo Observe — SDK package.

Re-exports the public entry points so callers can write:

    import contineo
    contineo.init(...)
    contineo.attach(app, agent_name="...")   # primary API — attach to graph
    contineo.observe(...)                    # decorator API — attach to function
    contineo.get_timeline(...)
    contineo.last_session_id()
"""

from contineo.sdk.init import init
from contineo.sdk.attach import attach
from contineo.sdk.decorator import observe
from contineo.sdk.timeline import get_timeline, last_session_id

__all__ = [
    "init",
    "attach",
    "observe",
    "get_timeline",
    "last_session_id",
]
