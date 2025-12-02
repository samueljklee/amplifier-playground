"""Session runner that wraps AmplifierSession with event streaming support."""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any, Literal

from .protocols import EventCallback
from .ux_systems import WorkbenchApprovalSystem, WorkbenchDisplaySystem

logger = logging.getLogger(__name__)


class SessionRunner:
    """
    Runs AmplifierSession with event streaming support.

    Wraps AmplifierSession and:
    - Injects WorkbenchApprovalSystem and WorkbenchDisplaySystem
    - Registers an event capture hook to stream all events
    - Provides clean start/prompt/stop interface
    """

    def __init__(
        self,
        mount_plan: dict[str, Any],
        event_callback: EventCallback | None = None,
        approval_mode: Literal["auto", "deny", "queue"] = "auto",
        session_id: str | None = None,
        modules_dirs: list[Path | str] | Path | str | None = None,
    ):
        """
        Initialize session runner.

        Args:
            mount_plan: Mount plan configuration dict
            event_callback: Callback for event streaming (CLI prints JSONL, Web sends SSE)
            approval_mode: How to handle approval requests
            session_id: Optional explicit session ID (generated if not provided)
            modules_dirs: Directory or list of directories containing amplifier modules.
                         Modules should be in subdirectories like amplifier-module-provider-anthropic/
                         Directories are searched in order (first match wins).
        """
        self.mount_plan = mount_plan
        self.event_callback = event_callback
        self.approval_mode: Literal["auto", "deny", "queue"] = approval_mode
        self.session_id = session_id or str(uuid.uuid4())

        # Normalize modules_dirs to a list of Paths
        if modules_dirs is None:
            self.modules_dirs: list[Path] = []
        elif isinstance(modules_dirs, list):
            self.modules_dirs = [Path(d) for d in modules_dirs]
        else:
            self.modules_dirs = [Path(modules_dirs)]

        self._session: Any = None  # AmplifierSession, typed as Any to avoid import errors
        self._approval_system: WorkbenchApprovalSystem | None = None
        self._display_system: WorkbenchDisplaySystem | None = None
        self._started = False
        self._unregister_hook: Any = None

    async def start(self) -> str:
        """
        Start the session.

        Returns:
            Session ID

        Raises:
            RuntimeError: If session fails to start
            ImportError: If amplifier-core is not installed
        """
        if self._started:
            return self.session_id

        try:
            from amplifier_core.models import HookResult
            from amplifier_core.session import AmplifierSession
        except ImportError as e:
            raise ImportError("amplifier-core is required to run sessions") from e

        # Create UX systems
        self._approval_system = WorkbenchApprovalSystem(
            mode=self.approval_mode,
            event_callback=self.event_callback,
        )
        self._display_system = WorkbenchDisplaySystem(
            event_callback=self.event_callback,
        )

        # Create session
        self._session = AmplifierSession(
            config=self.mount_plan,
            session_id=self.session_id,
            approval_system=self._approval_system,
            display_system=self._display_system,
        )

        # Mount module source resolver if modules_dirs is provided
        # This must happen BEFORE initialize() so the loader can find modules
        if self.modules_dirs:
            try:
                from amplifier_module_resolution import StandardModuleSourceResolver

                resolver = StandardModuleSourceResolver(workspace_dir=self.modules_dirs)
                await self._session.coordinator.mount("module-source-resolver", resolver)
                logger.info(f"Mounted module source resolver with workspaces: {self.modules_dirs}")
            except ImportError:
                logger.warning(
                    "amplifier-module-resolution not installed. "
                    "Falling back to entry point discovery only."
                )

        # Initialize session (loads all modules)
        await self._session.initialize()

        # Register event capture hook
        if self.event_callback:
            hooks = self._session.coordinator.hooks

            async def capture_all_events(event: str, data: dict[str, Any]) -> HookResult:
                """Forward all events to callback."""
                try:
                    await self.event_callback(event, data)  # type: ignore
                except Exception as e:
                    logger.warning(f"Event callback failed for {event}: {e}")
                return HookResult(action="continue")

            # Register for all known events
            from amplifier_core.events import ALL_EVENTS

            for event_name in ALL_EVENTS:
                hooks.register(
                    event_name,
                    capture_all_events,
                    priority=1000,  # Low priority - run after other hooks
                    name=f"workbench-capture-{event_name}",
                )

        self._started = True

        # Emit our own start event
        if self.event_callback:
            await self.event_callback(
                "workbench:session_started",
                {
                    "session_id": self.session_id,
                    "mount_plan_summary": self._summarize_mount_plan(),
                },
            )

        logger.info(f"Session started: {self.session_id}")
        return self.session_id

    async def prompt(self, text: str) -> str:
        """
        Send a prompt and get response.

        Args:
            text: User prompt text

        Returns:
            Response string

        Raises:
            RuntimeError: If session not started
        """
        if not self._started or self._session is None:
            raise RuntimeError("Session not started. Call start() first.")

        return await self._session.execute(text)

    async def stop(self) -> None:
        """Stop and cleanup the session."""
        if not self._started:
            return

        if self._session:
            await self._session.cleanup()

        # Emit our own stop event
        if self.event_callback:
            await self.event_callback(
                "workbench:session_stopped",
                {"session_id": self.session_id},
            )

        self._started = False
        self._session = None
        logger.info(f"Session stopped: {self.session_id}")

    async def resolve_approval(self, decision: str) -> None:
        """
        Resolve a pending approval request.

        Called by API when user makes approval decision in UI.

        Args:
            decision: User's decision
        """
        if self._approval_system:
            await self._approval_system.resolve_approval(decision)

    def _summarize_mount_plan(self) -> dict[str, Any]:
        """Create a summary of the mount plan for events."""
        session = self.mount_plan.get("session", {})
        providers = self.mount_plan.get("providers", [])
        tools = self.mount_plan.get("tools", [])
        hooks = self.mount_plan.get("hooks", [])

        return {
            "orchestrator": session.get("orchestrator"),
            "context": session.get("context"),
            "provider_count": len(providers),
            "providers": [p.get("module") for p in providers],
            "tool_count": len(tools),
            "tools": [t.get("module") for t in tools],
            "hook_count": len(hooks),
        }

    @property
    def is_running(self) -> bool:
        """Check if session is currently running."""
        return self._started

    async def __aenter__(self) -> "SessionRunner":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.stop()


class SessionManager:
    """
    Manages multiple concurrent sessions.

    For web server use where multiple users may have active sessions.
    """

    def __init__(self):
        """Initialize session manager."""
        self._sessions: dict[str, SessionRunner] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        mount_plan: dict[str, Any],
        event_callback: EventCallback | None = None,
        approval_mode: Literal["auto", "deny", "queue"] = "auto",
        session_id: str | None = None,
        modules_dirs: list[Path | str] | Path | str | None = None,
    ) -> SessionRunner:
        """
        Create and start a new session.

        Args:
            mount_plan: Mount plan configuration
            event_callback: Event callback for this session
            approval_mode: Approval handling mode
            session_id: Optional explicit session ID
            modules_dirs: Directory or list of directories containing amplifier modules

        Returns:
            Started SessionRunner
        """
        runner = SessionRunner(
            mount_plan=mount_plan,
            event_callback=event_callback,
            approval_mode=approval_mode,
            session_id=session_id,
            modules_dirs=modules_dirs,
        )

        await runner.start()

        async with self._lock:
            self._sessions[runner.session_id] = runner

        return runner

    async def get(self, session_id: str) -> SessionRunner | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    async def stop(self, session_id: str) -> bool:
        """
        Stop a session.

        Returns:
            True if stopped, False if not found
        """
        async with self._lock:
            runner = self._sessions.pop(session_id, None)

        if runner:
            await runner.stop()
            return True
        return False

    async def stop_all(self) -> None:
        """Stop all sessions."""
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()

        for runner in sessions:
            try:
                await runner.stop()
            except Exception as e:
                logger.error(f"Error stopping session {runner.session_id}: {e}")

    def list_active(self) -> list[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())

    @property
    def active_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)
