"""Protocol definitions for the workbench."""

from typing import Any, Protocol


class EventCallback(Protocol):
    """Callback for session events - follows the save_callback pattern from scenarios toolkit."""

    async def __call__(self, event: str, data: dict[str, Any]) -> None:
        """
        Called when a session event occurs.

        Args:
            event: Event name (e.g., "session:start", "tool:pre", "provider:response")
            data: Event data payload
        """
        ...
