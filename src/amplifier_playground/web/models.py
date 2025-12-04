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
# Profile Models
# =============================================================================


class ProfileListItem(BaseModel):
    """Profile list item."""

    name: str  # Full name (collection:profile or just profile)
    collection: str | None = None
    profile: str
    path: str


class ProfileInfo(BaseModel):
    """Profile details."""

    name: str
    description: str | None = None
    extends: list[str] | None = None
    agents_count: int = 0
    context_count: int = 0
    has_system_prompt: bool = False


class CompiledProfile(BaseModel):
    """Compiled profile result."""

    profile_name: str
    mount_plan: dict[str, Any]


class ProfileContent(BaseModel):
    """Raw profile content."""

    name: str
    path: str
    content: str


class ProfileUpdateRequest(BaseModel):
    """Request to update profile content."""

    content: str


class DependencyFile(BaseModel):
    """A file in the profile dependency graph."""

    path: str
    name: str  # Display name (e.g., "base.md" or "@foundation:context/...")
    content: str
    file_type: str  # "profile", "context", "agent"
    relationship: str  # "root", "extends", "mentions", "agents"
    referenced_by: list[str] = Field(default_factory=list)  # Paths of files that reference this one


class ProfileDependencyGraph(BaseModel):
    """Full dependency graph for a profile."""

    profile_name: str
    files: list[DependencyFile]
    mount_plan: dict[str, Any] | None = None  # Compiled mount plan for the profile


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

    profile: str | None = None  # Primary: profile name (e.g., "foundation:base")
    config_id: str | None = None  # Legacy: saved config ID
    mount_plan: dict[str, Any] | None = None  # Advanced: raw mount plan
    approval_mode: str = "auto"
    modules_dirs: list[str] | None = Field(
        default=None,
        description="List of directories containing amplifier modules for runtime resolution. "
                    "Directories are searched in order (first match wins)."
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that profile, config_id, or mount_plan is provided."""
        if not self.profile and not self.config_id and not self.mount_plan:
            raise ValueError("One of profile, config_id, or mount_plan must be provided")


class SessionInfo(BaseModel):
    """Session information."""

    session_id: str
    is_running: bool
    profile: str | None = None
    config_id: str | None = None


class SessionDetailInfo(BaseModel):
    """Detailed session information."""

    session_id: str
    is_running: bool
    profile: str | None = None
    config_id: str | None = None
    parent_session_id: str | None = None
    mount_plan: dict[str, Any] | None = None
    approval_mode: str | None = None
    created_at: str | None = None


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
