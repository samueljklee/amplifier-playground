"""Module management routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from amplifier_playground.core import ModuleRegistry

from ..models import AddCustomModuleRequest, ModuleInfo, RegisterModuleRequest

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
            config=m.config,
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
        config=info.config,
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
        config=info.config,
    )


@router.post("/custom", response_model=ModuleInfo)
async def add_custom_module(request: AddCustomModuleRequest) -> ModuleInfo:
    """
    Add a custom module with git URL and configuration.

    This allows users to add custom providers, tools, orchestrators, context managers,
    or hooks that are not in the known module catalog.

    Example request:
    ```json
    {
        "module_id": "my-custom-provider",
        "name": "My Custom Provider",
        "category": "provider",
        "source": "git+https://github.com/myuser/my-provider@main",
        "description": "A custom LLM provider",
        "config": {
            "api_key_env": "MY_PROVIDER_API_KEY",
            "default_model": "my-model-v1"
        }
    }
    ```
    """
    registry = get_registry()

    try:
        registry.add_custom(
            module_id=request.module_id,
            name=request.name,
            category=request.category,
            source=request.source,
            description=request.description,
            config=request.config if request.config else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    info = registry.get_info(request.module_id)
    if not info:
        raise HTTPException(status_code=500, detail="Failed to add custom module")

    return ModuleInfo(
        id=info.id,
        name=info.name,
        category=info.category,
        description=info.description,
        version=info.version,
        source=info.source,
        config_schema=info.config_schema,
        config=info.config,
    )


@router.delete("/{module_id}")
async def remove_custom_module(module_id: str) -> dict:
    """
    Remove a custom or local module from the registry.

    Note: This only removes modules that were added via /custom or /register endpoints.
    Built-in known modules cannot be removed.
    """
    registry = get_registry()

    if registry.unregister_local(module_id):
        return {"status": "removed", "module_id": module_id}
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_id}' not found or is a built-in module that cannot be removed"
        )
