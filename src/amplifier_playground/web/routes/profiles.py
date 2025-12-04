"""Profile management routes."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from amplifier_playground.core import CollectionManager, get_required_credentials_for_providers
from amplifier_playground.core.mention_loader import MentionLoader, MentionResolver
from amplifier_profiles import (
    ProfileLoader,
    ProfileError,
    AgentLoader,
    AgentResolver,
    compile_profile_to_mount_plan,
)

from fastapi.responses import PlainTextResponse

from ..models import (
    ProfileInfo,
    ProfileListItem,
    CompiledProfile,
    ProfileContent,
    ProfileUpdateRequest,
    DependencyFile,
    ProfileDependencyGraph,
)
from amplifier_playground.core.mentions import parse_mentions

router = APIRouter(prefix="/profiles", tags=["profiles"])

# Shared instances
_collection_manager: CollectionManager | None = None


class CollectionResolverAdapter:
    """Adapter to make CollectionManager work with ProfileLoader and AgentResolver."""

    def __init__(self, collection_manager: CollectionManager):
        self._manager = collection_manager

    def resolve(self, collection_name: str) -> Path | None:
        """Resolve collection name to filesystem path."""
        return self._manager.resolve_collection(collection_name)


def get_collection_manager() -> CollectionManager:
    """Get or create the collection manager."""
    global _collection_manager
    if _collection_manager is None:
        _collection_manager = CollectionManager()
    return _collection_manager


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


@router.get("", response_model=list[ProfileListItem])
async def list_profiles() -> list[ProfileListItem]:
    """List all available profiles from collections and local directories."""
    manager = get_collection_manager()
    all_profiles: list[ProfileListItem] = []

    # Get profiles from each collection
    for coll in manager.list_collections():
        coll_profiles = manager.list_profiles_in_collection(coll.name)
        for p in coll_profiles:
            all_profiles.append(ProfileListItem(
                name=f"{coll.name}:{p.stem}",
                collection=coll.name,
                profile=p.stem,
                path=str(p),
            ))

    # Get local profiles
    local_paths = [
        Path.cwd() / ".amplifier" / "profiles",
        Path.home() / ".amplifier" / "profiles",
    ]

    for local_path in local_paths:
        if local_path.exists():
            for p in local_path.glob("*.md"):
                all_profiles.append(ProfileListItem(
                    name=p.stem,
                    collection=None,
                    profile=p.stem,
                    path=str(p),
                ))

    return all_profiles


def find_profile_path(manager: CollectionManager, profile_name: str) -> Path | None:
    """Find the actual file path for a profile.

    This handles both collection profiles (collection:profile) and local profiles.
    Uses list_profiles_in_collection to get actual paths, which works correctly
    even when resolve_collection returns a nested directory.
    """
    # Check collections first
    if ":" in profile_name:
        coll_name, prof_name = profile_name.split(":", 1)
        profiles = manager.list_profiles_in_collection(coll_name)
        for p in profiles:
            if p.stem == prof_name:
                return p
        return None

    # Check local paths
    local_paths = [
        Path.cwd() / ".amplifier" / "profiles",
        Path.home() / ".amplifier" / "profiles",
    ]
    for local_path in local_paths:
        candidate = local_path / f"{profile_name}.md"
        if candidate.exists():
            return candidate

    return None


@router.get("/{profile_name:path}/content", response_model=ProfileContent)
async def get_profile_content(profile_name: str) -> ProfileContent:
    """Get the raw markdown content of a profile."""
    manager = get_collection_manager()
    profile_path = find_profile_path(manager, profile_name)

    if not profile_path or not profile_path.exists():
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_name}")

    try:
        content = profile_path.read_text(encoding="utf-8")
        return ProfileContent(
            name=profile_name,
            path=str(profile_path),
            content=content,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read profile: {e}")


@router.put("/{profile_name:path}/content", response_model=ProfileContent)
async def update_profile_content(profile_name: str, request: ProfileUpdateRequest) -> ProfileContent:
    """Update the raw markdown content of a profile."""
    manager = get_collection_manager()
    profile_path = find_profile_path(manager, profile_name)

    if not profile_path or not profile_path.exists():
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_name}")

    try:
        profile_path.write_text(request.content, encoding="utf-8")
        return ProfileContent(
            name=profile_name,
            path=str(profile_path),
            content=request.content,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save profile: {e}")


@router.post("/{profile_name:path}/compile", response_model=CompiledProfile)
async def compile_profile(profile_name: str) -> CompiledProfile:
    """Compile a profile to a mount plan with full resolution."""
    manager = get_collection_manager()
    loader = build_profile_loader(manager)
    agent_loader = build_agent_loader(manager)

    try:
        profile = loader.load_profile(profile_name)
        mount_plan = compile_profile_to_mount_plan(profile, agent_loader=agent_loader)

        return CompiledProfile(
            profile_name=profile.profile.name,
            mount_plan=mount_plan,
        )
    except ProfileError as e:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_name} - {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compile profile: {e}")


def _resolve_extends_path(manager: CollectionManager, extends_ref: str, current_profile_path: Path) -> Path | None:
    """Resolve an extends reference to a file path.

    Handles multiple formats:
    - collection:profiles/name.md (explicit path)
    - collection:name (profile name, looks in profiles/ dir)
    - relative/path.md (relative to current profile)
    """
    # Handle collection:path format
    if ":" in extends_ref:
        coll_name, rel_path = extends_ref.split(":", 1)
        coll_path = manager.resolve_collection(coll_name)
        if coll_path:
            # Try as exact path first
            candidate = coll_path / rel_path
            if candidate.exists():
                return candidate

            # Try with .md extension
            if not rel_path.endswith(".md"):
                candidate = coll_path / f"{rel_path}.md"
                if candidate.exists():
                    return candidate

            # Try as profile name (in profiles/ directory)
            profile_name = rel_path.replace("profiles/", "").replace(".md", "")
            candidate = coll_path / "profiles" / f"{profile_name}.md"
            if candidate.exists():
                return candidate

            # Hybrid packaging: check parent directory
            candidate = coll_path.parent / rel_path
            if candidate.exists():
                return candidate
            candidate = coll_path.parent / "profiles" / f"{profile_name}.md"
            if candidate.exists():
                return candidate
    else:
        # Relative path from current profile
        candidate = current_profile_path.parent / extends_ref
        if candidate.exists():
            return candidate
        # Try with .md extension
        if not extends_ref.endswith(".md"):
            candidate = current_profile_path.parent / f"{extends_ref}.md"
            if candidate.exists():
                return candidate
    return None


def _resolve_agents_for_profile(
    manager: CollectionManager,
    profile_path: Path,
    agents_config: str | list[str] | dict,
) -> list[tuple[str, Path]]:
    """Resolve agent files for a profile.

    Returns list of (agent_name, agent_path) tuples.

    Supports three formats for agents_config:
    - "all": resolve all available agents
    - ["agent1", "agent2"]: resolve specific agents by name
    - {"dirs": ["./agents"], "include": ["agent1"]}: dict-based config with:
        - dirs: additional directories to search for agents (relative to profile)
        - include: specific agent names to include (filters discovered agents)
    """
    from amplifier_profiles import AgentResolver

    # Build search paths for agents
    search_paths: list[Path] = []
    resolver_adapter = CollectionResolverAdapter(manager)

    # Local agents
    local_agents = Path.cwd() / ".amplifier" / "agents"
    if local_agents.exists():
        search_paths.append(local_agents)
    user_agents = Path.home() / ".amplifier" / "agents"
    if user_agents.exists():
        search_paths.append(user_agents)

    # Collection agents
    for coll in manager.list_collections():
        coll_path = manager.resolve_collection(coll.name)
        if coll_path:
            agents_path = coll_path / "agents"
            if agents_path.exists():
                search_paths.append(agents_path)
            # Hybrid packaging: also check parent
            parent_agents = coll_path.parent / "agents"
            if parent_agents.exists() and parent_agents not in search_paths:
                search_paths.append(parent_agents)

    # Handle dict-based AgentsConfig format with dirs and include
    include_filter: list[str] | None = None
    if isinstance(agents_config, dict):
        # Extract dirs - additional directories to search (relative to profile)
        dirs = agents_config.get("dirs")
        if dirs and isinstance(dirs, list):
            profile_dir = profile_path.parent
            for dir_path in dirs:
                # Resolve relative to profile location
                resolved_dir = (profile_dir / dir_path).resolve()
                if resolved_dir.exists() and resolved_dir not in search_paths:
                    search_paths.append(resolved_dir)

        # Extract include - specific agents to filter
        include = agents_config.get("include")
        if include and isinstance(include, list):
            include_filter = include

    resolver = AgentResolver(search_paths=search_paths, collection_resolver=resolver_adapter)

    results: list[tuple[str, Path]] = []

    if agents_config == "all":
        # Get all available agents
        for agent_name in resolver.list_agents():
            agent_path = resolver.resolve(agent_name)
            if agent_path and agent_path.exists():
                results.append((agent_name, agent_path))
    elif isinstance(agents_config, list):
        # Resolve specific agents (simple list format)
        for agent_name in agents_config:
            agent_path = resolver.resolve(agent_name)
            if agent_path and agent_path.exists():
                results.append((agent_name, agent_path))
    elif isinstance(agents_config, dict):
        # Dict-based AgentsConfig format
        if include_filter:
            # Resolve only the included agents
            for agent_name in include_filter:
                agent_path = resolver.resolve(agent_name)
                if agent_path and agent_path.exists():
                    results.append((agent_name, agent_path))
        else:
            # No include filter - get all agents from the search paths
            for agent_name in resolver.list_agents():
                agent_path = resolver.resolve(agent_name)
                if agent_path and agent_path.exists():
                    results.append((agent_name, agent_path))

    return results


def _build_dependency_graph(
    manager: CollectionManager,
    mention_resolver: MentionResolver,
    profile_path: Path,
    profile_name: str,
) -> list[DependencyFile]:
    """Recursively build dependency graph for a profile.

    Tracks multiple referrers when the same file is referenced by different files.
    """
    import yaml

    # Track files by path to accumulate multiple referrers
    files_by_path: dict[str, DependencyFile] = {}
    # Track which files have been processed (to avoid infinite recursion)
    processed: set[Path] = set()

    def add_file(
        path: Path,
        name: str,
        file_type: str,
        relationship: str,
        referenced_by: str | None,
    ) -> None:
        path_str = str(path)

        # If file already exists, just add the referrer if not already present
        if path_str in files_by_path:
            if referenced_by and referenced_by not in files_by_path[path_str].referenced_by:
                files_by_path[path_str].referenced_by.append(referenced_by)
            return

        # Skip if we've already processed this file (to prevent infinite recursion)
        if path in processed:
            return
        processed.add(path)

        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            return

        # Create the file entry with initial referrer
        referrers = [referenced_by] if referenced_by else []
        files_by_path[path_str] = DependencyFile(
            path=path_str,
            name=name,
            content=content,
            file_type=file_type,
            relationship=relationship,
            referenced_by=referrers,
        )

        # Parse extends and agents from YAML frontmatter if this is a profile
        if file_type == "profile":
            parts = content.split("---")
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])

                    # Handle extends
                    extends = frontmatter.get("profile", {}).get("extends")
                    if extends:
                        extends_list = extends if isinstance(extends, list) else [extends]
                        for ext in extends_list:
                            ext_path = _resolve_extends_path(manager, ext, path)
                            if ext_path:
                                add_file(ext_path, ext, "profile", "extends", path_str)

                    # Handle agents
                    agents_config = frontmatter.get("agents")
                    if agents_config:
                        agent_files = _resolve_agents_for_profile(manager, path, agents_config)
                        for agent_name, agent_path in agent_files:
                            add_file(agent_path, agent_name, "agent", "agents", path_str)

                except yaml.YAMLError:
                    pass

        # Parse @mentions
        mentions = parse_mentions(content)
        for mention in mentions:
            # Use mention resolver to get actual path
            mention_resolver.relative_to = path.parent
            resolved = mention_resolver.resolve(mention)
            if resolved and resolved.exists():
                add_file(resolved, mention, "context", "mentions", path_str)

    # Start with the root profile
    add_file(profile_path, profile_name, "profile", "root", None)

    # Return files in order: root first, then as discovered
    return list(files_by_path.values())


@router.get("/{profile_name:path}/graph", response_model=ProfileDependencyGraph)
async def get_profile_dependency_graph(profile_name: str) -> ProfileDependencyGraph:
    """Get the full dependency graph for a profile.

    Returns all connected files including:
    - The profile itself
    - Parent profiles (via extends)
    - Context files (via @mentions)
    - Recursively follows all references
    - The compiled mount plan
    """
    manager = get_collection_manager()
    profile_path = find_profile_path(manager, profile_name)

    if not profile_path or not profile_path.exists():
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_name}")

    mention_resolver = MentionResolver(collection_manager=manager)
    files = _build_dependency_graph(manager, mention_resolver, profile_path, profile_name)

    # Also compile the mount plan
    mount_plan: dict[str, Any] | None = None
    try:
        loader = build_profile_loader(manager)
        agent_loader = build_agent_loader(manager)
        profile = loader.load_profile(profile_name)
        mount_plan = compile_profile_to_mount_plan(profile, agent_loader=agent_loader)
    except Exception:
        # If compilation fails, just return without mount_plan
        pass

    return ProfileDependencyGraph(
        profile_name=profile_name,
        files=files,
        mount_plan=mount_plan,
    )


@router.get("/{profile_name:path}/credentials")
async def get_profile_credentials(profile_name: str) -> dict[str, Any]:
    """Get required credentials for a profile based on its providers.

    Compiles the profile to extract provider modules, then checks
    which credentials are needed and whether they're configured.

    Returns:
        {
            "profile": "foundation:base",
            "providers": ["amplifier-module-provider-anthropic"],
            "credentials": [
                {
                    "provider": "amplifier-module-provider-anthropic",
                    "credential_key": "anthropic_api_key",
                    "env_var": "ANTHROPIC_API_KEY",
                    "configured": true,
                    "display_name": "Anthropic API Key"
                }
            ],
            "ready": true  # true if all required credentials are configured
        }
    """
    manager = get_collection_manager()
    loader = build_profile_loader(manager)
    agent_loader = build_agent_loader(manager)

    try:
        profile = loader.load_profile(profile_name)
        mount_plan = compile_profile_to_mount_plan(profile, agent_loader=agent_loader)

        # Extract provider modules from mount plan
        providers = mount_plan.get("providers", [])
        provider_modules = [p.get("module", "") for p in providers if p.get("module")]

        # Get credential requirements
        credentials = get_required_credentials_for_providers(provider_modules)

        # Check if all required credentials are configured
        ready = all(c.get("configured", False) for c in credentials) if credentials else True

        return {
            "profile": profile_name,
            "providers": provider_modules,
            "credentials": credentials,
            "ready": ready,
        }
    except ProfileError as e:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_name} - {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check credentials: {e}")


@router.get("/{profile_name:path}", response_model=ProfileInfo)
async def get_profile(profile_name: str) -> ProfileInfo:
    """Get profile details including metadata."""
    manager = get_collection_manager()
    loader = build_profile_loader(manager)

    try:
        profile = loader.load_profile(profile_name)
        return ProfileInfo(
            name=profile.profile.name,
            description=profile.profile.description,
            extends=profile.profile.extends,
            agents_count=len(profile.agents) if profile.agents else 0,
            context_count=len(profile.context) if profile.context else 0,
            has_system_prompt=profile.system_prompt is not None,
        )
    except ProfileError as e:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_name} - {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load profile: {e}")
