"""
EventBus interface.

Every concrete bus implementation must satisfy this protocol.
Services depend on this interface, never on a specific implementation.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Protocol, Union

from contineo.events.base import BaseEvent, EventType

# A handler can be sync or async
EventHandler = Callable[[BaseEvent], Union[None, Awaitable[None]]]


class EventBusProtocol(Protocol):
    """Abstract interface for the Contineo Observe Event Bus.

    Concrete implementations (in-process, Redis Streams, etc.) must
    satisfy this protocol. Services should type-hint against this
    interface rather than a specific implementation.
    """

    async def publish(self, event: BaseEvent) -> None:
        """Publish an event to all registered subscribers.

        The call returns after all handlers have been dispatched.
        Handler errors must never propagate to the caller.

        Args:
            event: The immutable event to publish.
        """
        ...

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> str:
        """Register a handler for a specific event type.

        Args:
            event_type: The event type this handler should receive.
            handler:    Sync or async callable that accepts a BaseEvent.

        Returns:
            A subscription ID that can be used to unsubscribe later.
        """
        ...

    def subscribe_all(self, handler: EventHandler) -> str:
        """Register a handler that receives every event type.

        Args:
            handler: Sync or async callable that accepts a BaseEvent.

        Returns:
            A subscription ID that can be used to unsubscribe later.
        """
        ...

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a previously registered handler.

        Args:
            subscription_id: The ID returned by ``subscribe`` or
                             ``subscribe_all``.

        Returns:
            True if the subscription was found and removed, False if the
            ID was not recognised.
        """
        ...

    async def shutdown(self) -> None:
        """Gracefully shut down the bus and release resources."""
        ...
