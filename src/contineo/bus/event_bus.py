"""
In-process async Event Bus implementation.

This is the default EventBus for single-process deployments.
It dispatches events to all registered handlers concurrently using
asyncio.gather, fully isolating handler errors from one another and
from the publisher.

Usage::

    from contineo.bus import EventBus

    bus = EventBus()

    async def on_llm(event):
        print(event.event_type, event.model)

    bus.subscribe(EventType.LLM_COMPLETED, on_llm)

    await bus.publish(LLMCompletedEvent(...))
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from contineo.bus.flags import FeatureFlags
from contineo.bus.interface import EventHandler
from contineo.events.base import BaseEvent, EventType

logger = logging.getLogger("contineo.bus")


@dataclass
class _Subscription:
    """Internal record of a single subscriber."""

    subscription_id: str
    event_type: EventType | None  # None means "all events"
    handler: EventHandler


class EventBus:
    """In-process publish/subscribe Event Bus.

    Guarantees:
    - Handlers are dispatched concurrently via ``asyncio.gather``.
    - A crash in one handler never prevents other handlers from running.
    - Every error in a handler is emitted as a structured log entry that
      includes ``trace_id``, ``session_id``, and ``service`` fields.
    - Sync handlers are wrapped and run in the default thread executor so
      they do not block the event loop.
    - Subscriptions are identified by a UUID string so they can be removed
      individually.

    Args:
        flags: Feature flags that control which services are active.
               Defaults to loading from the current environment.
    """

    def __init__(self, flags: FeatureFlags | None = None) -> None:
        self._flags: FeatureFlags = flags or FeatureFlags.load()
        # Map from EventType → list of subscriptions for that specific type
        self._typed: dict[EventType, list[_Subscription]] = defaultdict(list)
        # Wildcard subscriptions (subscribe_all)
        self._wildcard: list[_Subscription] = []
        # Fast lookup: subscription_id → subscription (for unsubscribe)
        self._index: dict[str, _Subscription] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def publish(self, event: BaseEvent) -> None:
        """Dispatch an event to every matching subscriber concurrently.

        Errors raised by individual handlers are caught, logged with full
        context, and never re-raised to the caller.

        Args:
            event: The immutable event to publish.
        """
        if self._flags.bus_logging:
            logger.debug(
                "Publishing event",
                extra={
                    "event_type": event.event_type.value,
                    "event_id": event.event_id,
                    "session_id": event.session_id,
                    "trace_id": event.trace_id,
                    "service": "event_bus",
                },
            )

        handlers = self._collect_handlers(event.event_type)

        if not handlers:
            return

        await asyncio.gather(
            *[self._safe_dispatch(sub, event) for sub in handlers],
            return_exceptions=False,  # errors are handled inside _safe_dispatch
        )

    def subscribe(self, event_type: EventType, handler: EventHandler) -> str:
        """Register a handler for a specific event type.

        Args:
            event_type: The event type this handler should receive.
            handler:    Sync or async callable accepting a ``BaseEvent``.

        Returns:
            Subscription ID (UUID string) for use with ``unsubscribe``.
        """
        sub = _Subscription(
            subscription_id=str(uuid.uuid4()),
            event_type=event_type,
            handler=handler,
        )
        self._typed[event_type].append(sub)
        self._index[sub.subscription_id] = sub
        logger.debug(
            "Subscribed handler",
            extra={
                "subscription_id": sub.subscription_id,
                "event_type": event_type.value,
                "handler": _handler_name(handler),
                "service": "event_bus",
            },
        )
        return sub.subscription_id

    def subscribe_all(self, handler: EventHandler) -> str:
        """Register a handler that receives every event type.

        Args:
            handler: Sync or async callable accepting a ``BaseEvent``.

        Returns:
            Subscription ID (UUID string) for use with ``unsubscribe``.
        """
        sub = _Subscription(
            subscription_id=str(uuid.uuid4()),
            event_type=None,
            handler=handler,
        )
        self._wildcard.append(sub)
        self._index[sub.subscription_id] = sub
        logger.debug(
            "Subscribed wildcard handler",
            extra={
                "subscription_id": sub.subscription_id,
                "handler": _handler_name(handler),
                "service": "event_bus",
            },
        )
        return sub.subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a previously registered handler.

        Args:
            subscription_id: The ID returned by ``subscribe`` or
                             ``subscribe_all``.

        Returns:
            True if removed, False if the ID was not found.
        """
        sub = self._index.pop(subscription_id, None)
        if sub is None:
            return False

        if sub.event_type is None:
            self._wildcard = [s for s in self._wildcard if s.subscription_id != subscription_id]
        else:
            self._typed[sub.event_type] = [
                s
                for s in self._typed[sub.event_type]
                if s.subscription_id != subscription_id
            ]

        logger.debug(
            "Unsubscribed handler",
            extra={
                "subscription_id": subscription_id,
                "service": "event_bus",
            },
        )
        return True

    async def shutdown(self) -> None:
        """Clear all subscriptions and release resources."""
        self._typed.clear()
        self._wildcard.clear()
        self._index.clear()
        logger.info(
            "EventBus shut down",
            extra={"service": "event_bus"},
        )

    # ------------------------------------------------------------------
    # Introspection helpers (useful for tests and dashboards)
    # ------------------------------------------------------------------

    @property
    def subscriber_count(self) -> int:
        """Total number of active subscriptions (typed + wildcard)."""
        return len(self._index)

    def subscriber_count_for(self, event_type: EventType) -> int:
        """Number of handlers that will fire for a given event type.

        Includes both typed subscribers and wildcard subscribers.
        """
        return len(self._typed.get(event_type, [])) + len(self._wildcard)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_handlers(self, event_type: EventType) -> list[_Subscription]:
        """Return all subscriptions that should receive this event type."""
        return list(self._typed.get(event_type, [])) + list(self._wildcard)

    async def _safe_dispatch(self, sub: _Subscription, event: BaseEvent) -> None:
        """Invoke a single handler, catching and logging any exception."""
        try:
            if inspect.iscoroutinefunction(sub.handler):
                await sub.handler(event)
            else:
                # Run sync handler in the default executor to avoid blocking
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, sub.handler, event)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Handler raised an exception — other subscribers unaffected",
                extra={
                    "subscription_id": sub.subscription_id,
                    "handler": _handler_name(sub.handler),
                    "event_type": event.event_type.value,
                    "event_id": event.event_id,
                    "session_id": event.session_id,
                    "trace_id": event.trace_id,
                    "service": "event_bus",
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------


def _handler_name(handler: EventHandler) -> str:
    """Return a human-readable name for a handler callable."""
    return getattr(handler, "__qualname__", None) or getattr(handler, "__name__", repr(handler))
