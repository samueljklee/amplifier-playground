"""Configuration management routes."""

from fastapi import APIRouter, HTTPException

from amplifier_workbench.core import ConfigManager

from ..models import CreateConfigRequest, MountPlanConfig, UpdateConfigRequest

router = APIRouter(prefix="/configs", tags=["configs"])

# Shared config manager instance
_manager: ConfigManager | None = None


def get_manager() -> ConfigManager:
    """Get or create the config manager."""
    global _manager
    if _manager is None:
        _manager = ConfigManager()
    return _manager


@router.get("", response_model=list[MountPlanConfig])
async def list_configs(tag: str | None = None) -> list[MountPlanConfig]:
    """List saved configurations."""
    manager = get_manager()
    tags = [tag] if tag else None
    configs = manager.list_configs(tags=tags)

    return [
        MountPlanConfig(
            id=c.id,
            name=c.name,
            description=c.description,
            mount_plan=c.mount_plan,
            created_at=c.created_at,
            updated_at=c.updated_at,
            tags=c.tags,
        )
        for c in configs
    ]


@router.get("/{config_id}", response_model=MountPlanConfig)
async def get_config(config_id: str) -> MountPlanConfig:
    """Get a specific configuration."""
    manager = get_manager()
    cfg = manager.get_config(config_id)

    if not cfg:
        raise HTTPException(status_code=404, detail=f"Configuration not found: {config_id}")

    return MountPlanConfig(
        id=cfg.id,
        name=cfg.name,
        description=cfg.description,
        mount_plan=cfg.mount_plan,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
        tags=cfg.tags,
    )


@router.post("", response_model=MountPlanConfig)
async def create_config(request: CreateConfigRequest) -> MountPlanConfig:
    """Create a new configuration."""
    manager = get_manager()

    cfg = manager.create_config(
        name=request.name,
        mount_plan=request.mount_plan,
        description=request.description,
        tags=request.tags if request.tags else None,
    )

    return MountPlanConfig(
        id=cfg.id,
        name=cfg.name,
        description=cfg.description,
        mount_plan=cfg.mount_plan,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
        tags=cfg.tags,
    )


@router.put("/{config_id}", response_model=MountPlanConfig)
async def update_config(config_id: str, request: UpdateConfigRequest) -> MountPlanConfig:
    """Update a configuration."""
    manager = get_manager()

    cfg = manager.update_config(
        config_id=config_id,
        name=request.name,
        mount_plan=request.mount_plan,
        description=request.description,
        tags=request.tags,
    )

    if not cfg:
        raise HTTPException(status_code=404, detail=f"Configuration not found: {config_id}")

    return MountPlanConfig(
        id=cfg.id,
        name=cfg.name,
        description=cfg.description,
        mount_plan=cfg.mount_plan,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
        tags=cfg.tags,
    )


@router.delete("/{config_id}")
async def delete_config(config_id: str) -> dict:
    """Delete a configuration."""
    manager = get_manager()

    if not manager.get_config(config_id):
        raise HTTPException(status_code=404, detail=f"Configuration not found: {config_id}")

    manager.delete_config(config_id)
    return {"deleted": config_id}
