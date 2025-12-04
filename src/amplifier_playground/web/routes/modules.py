"""Module management routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from amplifier_playground.core import ModuleRegistry

from ..models import ModuleInfo, RegisterModuleRequest

router = APIRouter(prefix="/modules", tags=["modules"])

# Shared registry instance
_registry: ModuleRegistry | None = None


def get_registry() -> ModuleRegistry:
    """Get or create the module registry."""
    global _registry
    if _registry is None:
        _registry = ModuleRegistry()
    return _registry


@router.get("", response_model=list[ModuleInfo])
async def list_modules(category: str | None = None) -> list[ModuleInfo]:
    """List available modules."""
    registry = get_registry()

    if category:
        modules = registry.list_by_category(category)
    else:
        modules = registry.list_all()

    return [
        ModuleInfo(
            id=m.id,
            name=m.name,
            category=m.category,
            description=m.description,
            version=m.version,
            source=m.source,
            config_schema=m.config_schema,
        )
        for m in modules
    ]


@router.get("/{module_id}", response_model=ModuleInfo)
async def get_module(module_id: str) -> ModuleInfo:
    """Get details about a specific module."""
    registry = get_registry()
    info = registry.get_info(module_id)

    if not info:
        raise HTTPException(status_code=404, detail=f"Module not found: {module_id}")

    return ModuleInfo(
        id=info.id,
        name=info.name,
        category=info.category,
        description=info.description,
        version=info.version,
        source=info.source,
        config_schema=info.config_schema,
    )


@router.post("/register", response_model=ModuleInfo)
async def register_module(request: RegisterModuleRequest) -> ModuleInfo:
    """Register a local development module."""
    registry = get_registry()

    registry.register_local(
        module_id=request.module_id,
        name=request.name,
        category=request.category,
        path=Path(request.path),
        description=request.description,
    )

    info = registry.get_info(request.module_id)
    if not info:
        raise HTTPException(status_code=500, detail="Failed to register module")

    return ModuleInfo(
        id=info.id,
        name=info.name,
        category=info.category,
        description=info.description,
        version=info.version,
        source=info.source,
        config_schema=info.config_schema,
    )
