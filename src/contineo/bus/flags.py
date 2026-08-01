"""
Feature flags for the Contineo Observe Event Bus and services.

Every feature is controlled by an environment variable.
Flags are read once at import time; set env vars before importing contineo.

Supported flags:
    CONTINEO_ENABLE_TIMELINE   (default: true)
    CONTINEO_ENABLE_REPLAY     (default: true)
    CONTINEO_ENABLE_ANALYTICS  (default: true)
    CONTINEO_ENABLE_COST       (default: true)
    CONTINEO_ENABLE_BUS_LOGGING (default: true)
"""

from __future__ import annotations

import os


def _flag(name: str, default: bool = True) -> bool:
    """Read a boolean environment variable.

    Accepts "1", "true", "yes" (case-insensitive) as True.
    Everything else (including absence) falls back to ``default``.
    """
    raw = os.environ.get(name, "").strip().lower()
    if raw == "":
        return default
    return raw in ("1", "true", "yes")


class FeatureFlags:
    """Runtime feature flags.

    All flags are evaluated once when the class is instantiated.
    Use ``FeatureFlags.load()`` to pick up the current environment.
    """

    def __init__(self) -> None:
        self.timeline: bool = _flag("CONTINEO_ENABLE_TIMELINE")
        self.replay: bool = _flag("CONTINEO_ENABLE_REPLAY")
        self.analytics: bool = _flag("CONTINEO_ENABLE_ANALYTICS")
        self.cost: bool = _flag("CONTINEO_ENABLE_COST")
        self.bus_logging: bool = _flag("CONTINEO_ENABLE_BUS_LOGGING")

    @classmethod
    def load(cls) -> "FeatureFlags":
        """Return a fresh FeatureFlags instance from the current environment."""
        return cls()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"FeatureFlags("
            f"timeline={self.timeline}, "
            f"replay={self.replay}, "
            f"analytics={self.analytics}, "
            f"cost={self.cost}, "
            f"bus_logging={self.bus_logging})"
        )
