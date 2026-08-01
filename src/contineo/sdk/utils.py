"""
Contineo Observe — SDK: internal utilities.

Small helpers shared across sdk modules.
"""

from __future__ import annotations

import asyncio
from typing import Any


def extract_input(args: tuple, kwargs: dict) -> str | None:
    """Best-effort: pull the first string argument as the session input."""
    for arg in args:
        if isinstance(arg, str):
            return arg[:500]
    for val in kwargs.values():
        if isinstance(val, str):
            return val[:500]
    return None


def extract_output(result: Any) -> str | None:
    """Best-effort: convert a return value to a string for the session."""
    if result is None:
        return None
    if isinstance(result, str):
        return result[:500]
    return str(result)[:500]


def fire(coro) -> None:
    """Schedule an async coroutine from a sync context without blocking."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)
