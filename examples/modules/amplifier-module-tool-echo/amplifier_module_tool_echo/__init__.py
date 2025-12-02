"""Echo Tool Module for Amplifier.

A simple example tool that echoes back messages and performs basic operations.
Used to demonstrate local module development and testing with Amplifier Workbench.
"""

import logging
from datetime import datetime
from typing import Any

from amplifier_core import ModuleCoordinator, ToolResult

__all__ = ["EchoTool", "TimeTool", "mount"]

logger = logging.getLogger(__name__)


class EchoTool:
    """Echo back messages with optional transformation."""

    name = "echo"
    description = """
Echo back a message, optionally with transformations.

This is a simple example tool for testing Amplifier module development.
It can echo messages as-is, uppercase, lowercase, or reversed.
"""

    def __init__(self, config: dict[str, Any], coordinator: ModuleCoordinator):
        """Initialize EchoTool."""
        self.config = config
        self.coordinator = coordinator
        self.prefix = config.get("prefix", "")

    @property
    def input_schema(self) -> dict:
        """Return JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to echo back",
                },
                "transform": {
                    "type": "string",
                    "enum": ["none", "upper", "lower", "reverse"],
                    "description": "Optional transformation to apply",
                    "default": "none",
                },
            },
            "required": ["message"],
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        """Execute the echo tool."""
        message = input.get("message", "")
        transform = input.get("transform", "none")

        result = message

        if transform == "upper":
            result = message.upper()
        elif transform == "lower":
            result = message.lower()
        elif transform == "reverse":
            result = message[::-1]

        if self.prefix:
            result = f"{self.prefix}{result}"

        return ToolResult(output=result)


class TimeTool:
    """Get the current time."""

    name = "current_time"
    description = """
Get the current date and time.

Returns the current timestamp in ISO format.
Useful for testing and demonstrating tool functionality.
"""

    def __init__(self, config: dict[str, Any], coordinator: ModuleCoordinator):
        """Initialize TimeTool."""
        self.config = config
        self.coordinator = coordinator
        self.timezone = config.get("timezone", "UTC")

    @property
    def input_schema(self) -> dict:
        """Return JSON schema for tool parameters."""
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["iso", "human", "unix"],
                    "description": "Output format for the time",
                    "default": "iso",
                },
            },
        }

    async def execute(self, input: dict[str, Any]) -> ToolResult:
        """Execute the time tool."""
        format_type = input.get("format", "iso")
        now = datetime.now()

        if format_type == "iso":
            result = now.isoformat()
        elif format_type == "human":
            result = now.strftime("%B %d, %Y at %I:%M %p")
        elif format_type == "unix":
            result = str(int(now.timestamp()))
        else:
            result = now.isoformat()

        return ToolResult(output=result)


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None) -> None:
    """Mount echo tools.

    Args:
        coordinator: Module coordinator for registering tools
        config: Module configuration with optional:
            - prefix: String to prepend to all echo responses
            - timezone: Timezone for time tool (default: UTC)

    Returns:
        None
    """
    config = config or {}

    tools = [
        EchoTool(config, coordinator),
        TimeTool(config, coordinator),
    ]

    for tool in tools:
        await coordinator.mount("tools", tool, name=tool.name)

    logger.info(f"Mounted {len(tools)} echo tools")
