"""Session management routes with SSE event streaming."""

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from amplifier_playground.core import CollectionManager, ConfigManager, SessionManager, SessionRunner
from amplifier_playground.core.mention_loader import MentionLoader, MentionResolver
from amplifier_profiles import (
    ProfileLoader,
    ProfileError,
    AgentLoader,
    AgentResolver,
    compile_profile_to_mount_plan,
)

from ..models import (
    ApprovalRequest,
    CreateSessionRequest,
    PromptRequest,
    PromptResponse,
    SessionInfo,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Shared instances
_session_manager: SessionManager | None = None
_config_manager: ConfigManager | None = None
_collection_manager: CollectionManager | None = None

# Event queues per session for SSE
_event_queues: dict[str, asyncio.Queue] = {}


def get_session_manager() -> SessionManager:
    """Get or create the session manager."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def get_config_manager() -> ConfigManager:
    """Get or create the config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def get_collection_manager() -> CollectionManager:
    """Get or create the collection manager."""
    global _collection_manager
    if _collection_manager is None:
        _collection_manager = CollectionManager()
    return _collection_manager


class CollectionResolverAdapter:
    """Adapter to make CollectionManager work with ProfileLoader and AgentResolver."""

    def __init__(self, collection_manager: CollectionManager):
        self._manager = collection_manager

    def resolve(self, collection_name: str) -> Path | None:
        """Resolve collection name to filesystem path."""
        return self._manager.resolve_collection(collection_name)


def build_profile_loader(coll_manager: CollectionManager) -> ProfileLoader:
    """Build a ProfileLoader with search paths."""
    resolver = CollectionResolverAdapter(coll_manager)

    # Build search paths for local profiles
    local_search_paths: list[Path] = []
    local_profiles = Path.cwd() / ".amplifier" / "profiles"
    if local_profiles.exists():
        local_search_paths.append(local_profiles)
    user_profiles = Path.home() / ".amplifier" / "profiles"
    if user_profiles.exists():
        local_search_paths.append(user_profiles)

    return ProfileLoader(
        search_paths=local_search_paths,
        collection_resolver=resolver,
    )


def build_agent_loader(coll_manager: CollectionManager) -> AgentLoader:
    """Build an AgentLoader with search paths and @mention support."""
    search_paths: list[Path] = []
    resolver_adapter = CollectionResolverAdapter(coll_manager)

    # Local agents directories
    local_agents = Path.cwd() / ".amplifier" / "agents"
    if local_agents.exists():
        search_paths.append(local_agents)

    user_agents = Path.home() / ".amplifier" / "agents"
    if user_agents.exists():
        search_paths.append(user_agents)

    # Collection agents directories
    for coll in coll_manager.list_collections():
        coll_path = coll_manager.resolve_collection(coll.name)
        if coll_path:
            agents_path = coll_path.parent / "agents"
            if agents_path.exists():
                search_paths.append(agents_path)

    agent_resolver = AgentResolver(
        search_paths=search_paths,
        collection_resolver=resolver_adapter,
    )

    # Create mention loader for @mention expansion
    mention_resolver = MentionResolver(collection_manager=coll_manager)
    mention_loader = MentionLoader(resolver=mention_resolver)

    return AgentLoader(resolver=agent_resolver, mention_loader=mention_loader)


def create_sse_event_callback(session_id: str):
    """Create an event callback that queues events for SSE streaming."""

    async def callback(event: str, data: dict[str, Any]) -> None:
        if session_id in _event_queues:
            await _event_queues[session_id].put({"event": event, "data": data})

    return callback


@router.post("", response_model=SessionInfo)
async def create_session(request: CreateSessionRequest) -> SessionInfo:
    """Create and start a new session."""
    manager = get_session_manager()
    config_manager = get_config_manager()
    collection_manager = get_collection_manager()

    # Get mount plan from profile, config, or request
    mount_plan: dict[str, Any]
    profile_name: str | None = None
    config_id: str | None = None

    if request.profile:
        # Primary path: compile profile to mount plan
        try:
            loader = build_profile_loader(collection_manager)
            agent_loader = build_agent_loader(collection_manager)
            profile = loader.load_profile(request.profile)
            mount_plan = compile_profile_to_mount_plan(profile, agent_loader=agent_loader)
            profile_name = request.profile
        except ProfileError as e:
            raise HTTPException(status_code=404, detail=f"Profile not found: {request.profile} - {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to compile profile: {e}")
    elif request.config_id:
        # Legacy path: use saved config
        cfg = config_manager.get_config(request.config_id)
        if not cfg:
            raise HTTPException(status_code=404, detail=f"Configuration not found: {request.config_id}")
        mount_plan = cfg.mount_plan
        config_id = request.config_id
    elif request.mount_plan:
        # Advanced path: raw mount plan
        mount_plan = request.mount_plan
    else:
        raise HTTPException(status_code=400, detail="One of profile, config_id, or mount_plan required")

    # Create a runner to get the session_id
    runner = SessionRunner(
        mount_plan=mount_plan,
        approval_mode=request.approval_mode,  # type: ignore
        modules_dirs=request.modules_dirs,
    )
    session_id = runner.session_id

    # Set up event queue and callback
    _event_queues[session_id] = asyncio.Queue()
    runner.event_callback = create_sse_event_callback(session_id)

    # Start the session via the manager
    await runner.start()

    # Register with manager
    async with manager._lock:
        manager._sessions[session_id] = runner

    return SessionInfo(
        session_id=session_id,
        is_running=runner.is_running,
        profile=profile_name,
        config_id=config_id,
    )


@router.get("", response_model=list[SessionInfo])
async def list_sessions() -> list[SessionInfo]:
    """List active sessions."""
    manager = get_session_manager()
    session_ids = manager.list_active()

    sessions = []
    for sid in session_ids:
        runner = await manager.get(sid)
        if runner:
            sessions.append(
                SessionInfo(
                    session_id=sid,
                    is_running=runner.is_running,
                )
            )

    return sessions


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str) -> SessionInfo:
    """Get session info."""
    manager = get_session_manager()
    runner = await manager.get(session_id)

    if not runner:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return SessionInfo(
        session_id=session_id,
        is_running=runner.is_running,
    )


@router.delete("/{session_id}")
async def stop_session(session_id: str) -> dict:
    """Stop a session."""
    manager = get_session_manager()

    if not await manager.stop(session_id):
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    # Clean up event queue
    if session_id in _event_queues:
        del _event_queues[session_id]

    return {"stopped": session_id}


@router.post("/{session_id}/prompt", response_model=PromptResponse)
async def send_prompt(session_id: str, request: PromptRequest) -> PromptResponse:
    """Send a prompt to a session."""
    manager = get_session_manager()
    runner = await manager.get(session_id)

    if not runner:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    response = await runner.prompt(request.text)

    return PromptResponse(
        response=response,
        session_id=session_id,
    )


@router.post("/{session_id}/approval")
async def resolve_approval(session_id: str, request: ApprovalRequest) -> dict:
    """Resolve a pending approval request."""
    manager = get_session_manager()
    runner = await manager.get(session_id)

    if not runner:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    await runner.resolve_approval(request.decision)

    return {"resolved": True, "decision": request.decision}


@router.get("/{session_id}/events")
async def stream_events(session_id: str):
    """Stream session events via SSE."""
    if session_id not in _event_queues:
        raise HTTPException(status_code=404, detail=f"Session not found or no events: {session_id}")

    async def event_generator():
        """Generate SSE events from the queue."""
        queue = _event_queues.get(session_id)
        if not queue:
            return

        try:
            while True:
                try:
                    # Wait for event with timeout to allow checking if session still exists
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield ": keepalive\n\n"
                except Exception:
                    break
        finally:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
