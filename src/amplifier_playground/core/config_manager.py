"""Configuration manager for mount plan storage."""

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path.home() / ".amplifier-playground" / "configs"


@dataclass
class MountPlanConfig:
    """A saved mount plan configuration."""

    id: str
    name: str
    mount_plan: dict[str, Any]
    created_at: str
    updated_at: str
    description: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MountPlanConfig":
        """Create from dictionary."""
        return cls(**data)


class ConfigManager:
    """
    Manages mount plan configurations with file-based JSON storage.

    Storage: ~/.amplifier-playground/configs/{config_id}.json
    """

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize config manager.

        Args:
            config_dir: Directory for config storage (default: ~/.amplifier-playground/configs)
        """
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _config_path(self, config_id: str) -> Path:
        """Get path for a config file."""
        # Sanitize ID for filename safety
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", config_id)
        return self.config_dir / f"{safe_id}.json"

    def _generate_id(self, name: str) -> str:
        """Generate a unique ID from name."""
        base_id = re.sub(r"[^a-zA-Z0-9_-]", "-", name.lower())
        base_id = re.sub(r"-+", "-", base_id).strip("-")

        if not base_id:
            base_id = "config"

        # Check for conflicts
        if not self._config_path(base_id).exists():
            return base_id

        # Add suffix for uniqueness
        for i in range(1, 100):
            candidate = f"{base_id}-{i}"
            if not self._config_path(candidate).exists():
                return candidate

        # Fallback to UUID
        return f"{base_id}-{uuid.uuid4().hex[:8]}"

    def create(
        self,
        name: str,
        mount_plan: dict[str, Any],
        description: str | None = None,
        tags: list[str] | None = None,
        config_id: str | None = None,
    ) -> MountPlanConfig:
        """
        Create a new configuration.

        Args:
            name: Human-readable name
            mount_plan: The mount plan configuration
            description: Optional description
            tags: Optional tags for organization
            config_id: Optional explicit ID (generated from name if not provided)

        Returns:
            Created MountPlanConfig

        Raises:
            ValueError: If config_id already exists
        """
        if config_id is None:
            config_id = self._generate_id(name)
        else:
            # Check for conflict with explicit ID
            if self._config_path(config_id).exists():
                raise ValueError(f"Config with ID '{config_id}' already exists")

        now = datetime.now().isoformat()
        config = MountPlanConfig(
            id=config_id,
            name=name,
            mount_plan=mount_plan,
            created_at=now,
            updated_at=now,
            description=description,
            tags=tags or [],
        )

        self._save(config)
        logger.info(f"Created config: {config_id}")
        return config

    def get(self, config_id: str) -> MountPlanConfig | None:
        """
        Get a configuration by ID.

        Args:
            config_id: Configuration identifier

        Returns:
            MountPlanConfig if found, None otherwise
        """
        path = self._config_path(config_id)
        if not path.exists():
            return None

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return MountPlanConfig.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load config {config_id}: {e}")
            return None

    def update(
        self,
        config_id: str,
        name: str | None = None,
        mount_plan: dict[str, Any] | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
    ) -> MountPlanConfig | None:
        """
        Update an existing configuration.

        Args:
            config_id: Configuration identifier
            name: New name (optional)
            mount_plan: New mount plan (optional)
            description: New description (optional)
            tags: New tags (optional)

        Returns:
            Updated MountPlanConfig, or None if not found
        """
        config = self.get(config_id)
        if config is None:
            return None

        if name is not None:
            config.name = name
        if mount_plan is not None:
            config.mount_plan = mount_plan
        if description is not None:
            config.description = description
        if tags is not None:
            config.tags = tags

        config.updated_at = datetime.now().isoformat()

        self._save(config)
        logger.info(f"Updated config: {config_id}")
        return config

    def delete(self, config_id: str) -> bool:
        """
        Delete a configuration.

        Args:
            config_id: Configuration identifier

        Returns:
            True if deleted, False if not found
        """
        path = self._config_path(config_id)
        if not path.exists():
            return False

        path.unlink()
        logger.info(f"Deleted config: {config_id}")
        return True

    def list_all(self) -> list[MountPlanConfig]:
        """
        List all configurations.

        Returns:
            List of all configs, sorted by updated_at descending
        """
        configs = []
        for path in self.config_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                configs.append(MountPlanConfig.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load config {path.name}: {e}")

        return sorted(configs, key=lambda c: c.updated_at, reverse=True)

    def list_by_tag(self, tag: str) -> list[MountPlanConfig]:
        """
        List configurations with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of matching configs
        """
        return [c for c in self.list_all() if tag in c.tags]

    def list_configs(self, tags: list[str] | None = None) -> list[MountPlanConfig]:
        """
        List configurations with optional tag filtering.

        Args:
            tags: Optional list of tags to filter by (matches any)

        Returns:
            List of matching configs
        """
        configs = self.list_all()
        if tags:
            configs = [c for c in configs if any(tag in c.tags for tag in tags)]
        return configs

    # Aliases for consistent naming
    create_config = create
    get_config = get
    update_config = update
    delete_config = delete

    def _save(self, config: MountPlanConfig) -> None:
        """Save configuration to file."""
        path = self._config_path(config.id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

    def validate_mount_plan(self, mount_plan: dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate a mount plan structure.

        Args:
            mount_plan: Mount plan to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        session = mount_plan.get("session", {})
        if not session.get("orchestrator"):
            errors.append("Missing required field: session.orchestrator")
        if not session.get("context"):
            errors.append("Missing required field: session.context")

        # Check providers
        providers = mount_plan.get("providers", [])
        if not providers:
            errors.append("At least one provider is required")
        else:
            for i, provider in enumerate(providers):
                if not provider.get("module"):
                    errors.append(f"Provider {i}: missing 'module' field")

        # Check tools (optional but validate structure if present)
        for i, tool in enumerate(mount_plan.get("tools", [])):
            if not tool.get("module"):
                errors.append(f"Tool {i}: missing 'module' field")

        # Check hooks (optional but validate structure if present)
        for i, hook in enumerate(mount_plan.get("hooks", [])):
            if not hook.get("module"):
                errors.append(f"Hook {i}: missing 'module' field")

        return len(errors) == 0, errors

    def import_from_profile(self, profile_path: Path) -> MountPlanConfig:
        """
        Import configuration from an Amplifier profile.

        Args:
            profile_path: Path to profile markdown file

        Returns:
            Created MountPlanConfig

        Raises:
            ImportError: If amplifier-profiles not available
            ValueError: If profile is invalid
        """
        try:
            from amplifier_profiles.compiler import compile_profile_to_mount_plan  # type: ignore[import-not-found]
            from amplifier_profiles.loader import ProfileLoader  # type: ignore[import-not-found]
        except ImportError:
            raise ImportError("amplifier-profiles is required for profile import")

        # Load profile
        loader = ProfileLoader(search_paths=[profile_path.parent])
        profile = loader.load_profile(profile_path.stem)

        # Compile to mount plan
        mount_plan = compile_profile_to_mount_plan(profile)

        # Create config
        return self.create(
            name=profile_path.stem,
            mount_plan=mount_plan,
            description=f"Imported from profile: {profile_path}",
            tags=["imported", "profile"],
        )

    def export_to_profile(self, config_id: str, output_path: Path) -> Path:
        """
        Export configuration to Amplifier profile format.

        Args:
            config_id: Configuration identifier
            output_path: Path for output profile

        Returns:
            Path to created profile file

        Raises:
            ValueError: If config not found
        """
        config = self.get(config_id)
        if config is None:
            raise ValueError(f"Config not found: {config_id}")

        # Build YAML frontmatter from mount plan
        import yaml

        frontmatter = {"profile": {"name": config.name}}

        # Add session config
        session = config.mount_plan.get("session", {})
        if session:
            frontmatter["session"] = session

        # Add providers
        providers = config.mount_plan.get("providers", [])
        if providers:
            frontmatter["providers"] = providers

        # Add tools
        tools = config.mount_plan.get("tools", [])
        if tools:
            frontmatter["tools"] = tools

        # Add hooks
        hooks = config.mount_plan.get("hooks", [])
        if hooks:
            frontmatter["hooks"] = hooks

        # Write profile
        yaml_content = yaml.dump(frontmatter, default_flow_style=False)
        desc = config.description or ""
        content = f"---\n{yaml_content}---\n\n# {config.name}\n\n{desc}\n"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

        logger.info(f"Exported config {config_id} to {output_path}")
        return output_path
