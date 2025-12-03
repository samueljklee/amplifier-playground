"""Pydantic models for the web API."""

from typing import Any

from pydantic import BaseModel, Field

# =============================================================================
# Collection Models
# =============================================================================


class CollectionResourcesInfo(BaseModel):
    """Resources available in a collection."""

    profiles: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    context: list[str] = Field(default_factory=list)
    scenario_tools: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)


class CollectionInfo(BaseModel):
    """Collection information."""

    name: str
    path: str
    resources: CollectionResourcesInfo | None = None


# =============================================================================
# Module Models
# =============================================================================


class ModuleInfo(BaseModel):
    """Module information."""

    id: str
    name: str
    category: str
    description: str | None = None
    version: str | None = None
    source: str = "known"
    config_schema: dict[str, Any] | None = None


class RegisterModuleRequest(BaseModel):
    """Request to register a local module."""

    module_id: str
    name: str
    category: str
    path: str
    description: str | None = None


# =============================================================================
# Config Models
# =============================================================================


class MountPlanConfig(BaseModel):
    """Mount plan configuration."""

    id: str
    name: str
    description: str | None = None
    mount_plan: dict[str, Any]
    created_at: str  # ISO format string
    updated_at: str  # ISO format string
    tags: list[str] = Field(default_factory=list)


class CreateConfigRequest(BaseModel):
    """Request to create a configuration."""

    name: str
    mount_plan: dict[str, Any]
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class UpdateConfigRequest(BaseModel):
    """Request to update a configuration."""

    name: str | None = None
    mount_plan: dict[str, Any] | None = None
    description: str | None = None
    tags: list[str] | None = None


# =============================================================================
# Session Models
# =============================================================================


class CreateSessionRequest(BaseModel):
    """Request to create a session."""

    config_id: str | None = None
    mount_plan: dict[str, Any] | None = None
    approval_mode: str = "auto"
    modules_dirs: list[str] | None = Field(
        default=None,
        description="List of directories containing amplifier modules for runtime resolution. "
                    "Directories are searched in order (first match wins)."
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that either config_id or mount_plan is provided."""
        if not self.config_id and not self.mount_plan:
            raise ValueError("Either config_id or mount_plan must be provided")


class SessionInfo(BaseModel):
    """Session information."""

    session_id: str
    is_running: bool
    config_id: str | None = None


class PromptRequest(BaseModel):
    """Request to send a prompt."""

    text: str


class PromptResponse(BaseModel):
    """Response from a prompt."""

    response: str
    session_id: str


class ApprovalRequest(BaseModel):
    """Request to resolve an approval."""

    decision: str


# =============================================================================
# Event Models
# =============================================================================


class SessionEvent(BaseModel):
    """An event from a session."""

    event: str
    data: dict[str, Any]
    session_id: str
