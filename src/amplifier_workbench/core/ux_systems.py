"""UX system implementations for the workbench.

These implement the ApprovalSystem and DisplaySystem protocols from amplifier-core,
routing interactions through the event callback system.
"""

import asyncio
import logging
from typing import Any, Literal

from .protocols import EventCallback

logger = logging.getLogger(__name__)


class WorkbenchApprovalSystem:
    """
    Approval system for the workbench.

    Modes:
    - "auto": Auto-approve all requests (for testing)
    - "deny": Auto-deny all requests (for safety)
    - "queue": Queue to UI and wait for response (for interactive use)
    """

    def __init__(
        self,
        mode: Literal["auto", "deny", "queue"] = "auto",
        event_callback: EventCallback | None = None,
    ):
        """
        Initialize approval system.

        Args:
            mode: Approval mode
            event_callback: Callback for emitting approval events to UI
        """
        self.mode = mode
        self.event_callback = event_callback
        self._pending: asyncio.Queue[str] = asyncio.Queue()
        self._cache: dict[str, str] = {}  # Session-scoped cache for "always" decisions

    async def request_approval(
        self,
        prompt: str,
        options: list[str],
        timeout: float,
        default: Literal["allow", "deny"],
    ) -> str:
        """
        Request user approval with timeout.

        Args:
            prompt: Question to ask user
            options: Available choices (e.g., ["Allow", "Deny", "Allow always"])
            timeout: Seconds to wait for response
            default: Action to take on timeout

        Returns:
            Selected option string
        """
        # Check cache first
        cache_key = f"{prompt}:{','.join(options)}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            logger.debug(f"Using cached approval: {cached}")
            return cached

        # Handle auto modes
        if self.mode == "auto":
            logger.info(f"Auto-approving: {prompt}")
            return "Allow"

        if self.mode == "deny":
            logger.info(f"Auto-denying: {prompt}")
            return "Deny"

        # Queue mode: emit to UI and wait
        if self.event_callback:
            await self.event_callback(
                "approval:required",
                {
                    "prompt": prompt,
                    "options": options,
                    "timeout": timeout,
                    "default": default,
                },
            )

        try:
            async with asyncio.timeout(timeout):
                decision = await self._pending.get()

                # Cache "always" decisions
                if decision == "Allow always":
                    self._cache[cache_key] = "Allow"
                    logger.info(f"Cached approval for: {prompt[:50]}...")

                return decision

        except TimeoutError:
            logger.warning(f"Approval timeout after {timeout}s, using default: {default}")
            return "Allow" if default == "allow" else "Deny"

    async def resolve_approval(self, decision: str) -> None:
        """
        Resolve a pending approval request.

        Called by API/CLI when user makes a decision.

        Args:
            decision: User's decision (one of the options provided)
        """
        await self._pending.put(decision)

    def clear_cache(self) -> None:
        """Clear the approval cache."""
        self._cache.clear()


class WorkbenchDisplaySystem:
    """
    Display system that routes messages through the event callback.

    Messages are emitted as events so CLI can print them and Web can show them in UI.
    """

    def __init__(self, event_callback: EventCallback | None = None):
        """
        Initialize display system.

        Args:
            event_callback: Callback for emitting display events
        """
        self.event_callback = event_callback
        self._loop: asyncio.AbstractEventLoop | None = None

    def show_message(
        self,
        message: str,
        level: Literal["info", "warning", "error"],
        source: str = "hook",
    ) -> None:
        """
        Display message to user.

        Note: This is sync per the Protocol, but we need to emit async events.
        We handle this by scheduling the async call.

        Args:
            message: Message text
            level: Severity level
            source: Message source (for context)
        """
        # Log regardless
        log_fn = {"info": logger.info, "warning": logger.warning, "error": logger.error}.get(level, logger.info)
        log_fn(f"[{source}] {message}")

        # Emit event if callback provided
        if self.event_callback:
            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
                # Schedule the coroutine
                loop.create_task(self._emit_message(message, level, source))
            except RuntimeError:
                # No running loop - we're being called from sync context
                # Create a task that will run when loop is available
                logger.debug("No event loop available for display message emission")

    async def _emit_message(self, message: str, level: str, source: str) -> None:
        """Emit message as event."""
        if self.event_callback:
            await self.event_callback(
                "display:message",
                {
                    "message": message,
                    "level": level,
                    "source": source,
                },
            )


def create_cli_event_callback() -> EventCallback:
    """
    Create an event callback that prints JSONL to stdout.

    For CLI usage where events should be streamed as JSON lines.
    """
    import json
    import sys

    def serialize_value(obj: Any) -> Any:
        """Recursively serialize objects for JSON output."""
        # Handle Pydantic models
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        # Handle dataclasses
        if hasattr(obj, "__dataclass_fields__"):
            from dataclasses import asdict
            return asdict(obj)
        # Handle dicts recursively
        if isinstance(obj, dict):
            return {k: serialize_value(v) for k, v in obj.items()}
        # Handle lists recursively
        if isinstance(obj, list):
            return [serialize_value(item) for item in obj]
        # Return as-is for basic types
        return obj

    async def callback(event: str, data: dict[str, Any]) -> None:
        serialized_data = serialize_value(data)
        line = json.dumps({"event": event, "data": serialized_data}, ensure_ascii=False)
        print(line, file=sys.stdout, flush=True)

    return callback


def create_logging_event_callback(logger_name: str = "workbench.events") -> EventCallback:
    """
    Create an event callback that logs events.

    For debugging or when JSONL output isn't needed.
    """
    event_logger = logging.getLogger(logger_name)

    async def callback(event: str, data: dict[str, Any]) -> None:
        event_logger.debug(f"Event: {event}", extra={"event_data": data})

    return callback
