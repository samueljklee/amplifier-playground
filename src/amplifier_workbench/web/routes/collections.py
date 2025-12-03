"""Collection management routes."""

from fastapi import APIRouter, HTTPException

from amplifier_workbench.core import CollectionManager

from ..models import CollectionInfo, CollectionResourcesInfo

router = APIRouter(prefix="/collections", tags=["collections"])

# Shared manager instance
_manager: CollectionManager | None = None


def get_manager() -> CollectionManager:
    """Get or create the collection manager."""
    global _manager
    if _manager is None:
        _manager = CollectionManager()
    return _manager


@router.get("", response_model=list[CollectionInfo])
async def list_collections() -> list[CollectionInfo]:
    """List available collections."""
    manager = get_manager()
    collections = manager.list_collections()

    return [CollectionInfo(name=c.name, path=str(c.path)) for c in collections]


@router.get("/{collection_name}", response_model=CollectionInfo)
async def get_collection(collection_name: str) -> CollectionInfo:
    """Get details about a specific collection including its resources."""
    manager = get_manager()
    info = manager.get_collection_info(collection_name)

    if not info:
        raise HTTPException(status_code=404, detail=f"Collection not found: {collection_name}")

    resources = None
    if info.resources:
        resources = CollectionResourcesInfo(
            profiles=[str(p) for p in info.resources.profiles],
            agents=[str(a) for a in info.resources.agents],
            context=[str(c) for c in info.resources.context],
            scenario_tools=[str(s) for s in info.resources.scenario_tools],
            modules=[str(m) for m in info.resources.modules],
        )

    return CollectionInfo(name=info.name, path=str(info.path), resources=resources)


@router.get("/{collection_name}/profiles", response_model=list[str])
async def list_collection_profiles(collection_name: str) -> list[str]:
    """List profiles in a collection."""
    manager = get_manager()
    profiles = manager.list_profiles_in_collection(collection_name)

    if not profiles and not manager.resolve_collection(collection_name):
        raise HTTPException(status_code=404, detail=f"Collection not found: {collection_name}")

    return [p.stem for p in profiles]


@router.get("/{collection_name}/agents", response_model=list[str])
async def list_collection_agents(collection_name: str) -> list[str]:
    """List agents in a collection."""
    manager = get_manager()
    agents = manager.list_agents_in_collection(collection_name)

    if not agents and not manager.resolve_collection(collection_name):
        raise HTTPException(status_code=404, detail=f"Collection not found: {collection_name}")

    return [a.stem for a in agents]


@router.get("/{collection_name}/modules", response_model=list[str])
async def list_collection_modules(collection_name: str) -> list[str]:
    """List modules in a collection."""
    manager = get_manager()
    modules = manager.list_modules_in_collection(collection_name)

    if not modules and not manager.resolve_collection(collection_name):
        raise HTTPException(status_code=404, detail=f"Collection not found: {collection_name}")

    return [m.name for m in modules]
