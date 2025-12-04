"""Module registry for discovering and managing available modules."""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

ModuleType = Literal["provider", "tool", "orchestrator", "context", "hook"]


@dataclass
class ModuleInfo:
    """Information about an available module."""

    id: str
    name: str
    category: ModuleType  # renamed from 'type' to avoid keyword conflict
    description: str | None = None
    source: str = "known"  # git URL, local path, "entry-point", or "known"
    version: str | None = None
    installed: bool = False
    config_schema: dict | None = None  # JSON Schema for config options (future)


@dataclass
class ModuleRegistry:
    """
    Registry of available modules.

    Combines:
    - Discovered modules (via ModuleLoader.discover())
    - Known modules (curated list, may not be installed)
    - User-registered local modules (for development)
    """

    _discovered: dict[str, ModuleInfo] = field(default_factory=dict)
    _known: dict[str, ModuleInfo] = field(default_factory=dict)
    _local: dict[str, ModuleInfo] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize with known modules."""
        self._init_known_modules()

    def _init_known_modules(self):
        """Initialize curated list of known modules."""
        # Core modules that come with amplifier
        known = [
            ModuleInfo(
                id="loop-basic",
                name="Basic Loop Orchestrator",
                category="orchestrator",
                description="Simple request-response orchestration",
                source="amplifier-core",
            ),
            ModuleInfo(
                id="loop-streaming",
                name="Streaming Loop Orchestrator",
                category="orchestrator",
                description="Streaming response orchestration",
                source="amplifier-core",
            ),
            ModuleInfo(
                id="context-simple",
                name="Simple Context Manager",
                category="context",
                description="In-memory context (no persistence)",
                source="amplifier-core",
            ),
            ModuleInfo(
                id="context-persistent",
                name="Persistent Context Manager",
                category="context",
                description="File-based context with checkpointing",
                source="amplifier-core",
            ),
            ModuleInfo(
                id="provider-anthropic",
                name="Anthropic Provider",
                category="provider",
                description="Claude models via Anthropic API",
                source="git+https://github.com/microsoft/amplifier-modules#subdirectory=provider-anthropic",
            ),
            ModuleInfo(
                id="provider-openai",
                name="OpenAI Provider",
                category="provider",
                description="GPT models via OpenAI API",
                source="git+https://github.com/microsoft/amplifier-modules#subdirectory=provider-openai",
            ),
            ModuleInfo(
                id="provider-azure-openai",
                name="Azure OpenAI Provider",
                category="provider",
                description="GPT models via Azure OpenAI",
                source="git+https://github.com/microsoft/amplifier-modules#subdirectory=provider-azure-openai",
            ),
            ModuleInfo(
                id="provider-ollama",
                name="Ollama Provider",
                category="provider",
                description="Local models via Ollama",
                source="git+https://github.com/microsoft/amplifier-modules#subdirectory=provider-ollama",
            ),
            ModuleInfo(
                id="tool-filesystem",
                name="Filesystem Tool",
                category="tool",
                description="File read/write operations",
                source="git+https://github.com/microsoft/amplifier-modules#subdirectory=tool-filesystem",
            ),
            ModuleInfo(
                id="tool-shell",
                name="Shell Tool",
                category="tool",
                description="Shell command execution",
                source="git+https://github.com/microsoft/amplifier-modules#subdirectory=tool-shell",
            ),
            ModuleInfo(
                id="hooks-logging",
                name="Logging Hooks",
                category="hook",
                description="Event logging to file/console",
                source="git+https://github.com/microsoft/amplifier-modules#subdirectory=hooks-logging",
            ),
        ]

        for module in known:
            self._known[module.id] = module

    async def discover_local(self) -> list[ModuleInfo]:
        """
        Discover installed modules using ModuleLoader.

        Returns:
            List of discovered ModuleInfo
        """
        try:
            from amplifier_core.loader import ModuleLoader

            loader = ModuleLoader()
            discovered = await loader.discover()

            for info in discovered:
                module_info = ModuleInfo(
                    id=info.id,
                    name=info.name,
                    category=info.type,  # type: ignore
                    description=info.description,
                    version=info.version,
                    source="entry-point",
                    installed=True,
                )
                self._discovered[info.id] = module_info

            logger.info(f"Discovered {len(discovered)} installed modules")
            return list(self._discovered.values())

        except ImportError:
            logger.warning("amplifier-core not installed, skipping module discovery")
            return []
        except Exception as e:
            logger.error(f"Module discovery failed: {e}")
            return []

    def register_local(
        self,
        module_id: str,
        name: str,
        category: str,
        path: Path,
        description: str | None = None,
    ) -> ModuleInfo:
        """
        Register a local module being developed.

        Args:
            module_id: Module identifier (e.g., "my-custom-tool")
            name: Display name for the module
            category: Module category (provider, tool, orchestrator, context, hook)
            path: Path to module directory
            description: Optional description

        Returns:
            Created ModuleInfo

        Raises:
            ValueError: If path doesn't exist or is invalid
        """
        if not path.exists():
            raise ValueError(f"Module path does not exist: {path}")

        # Check for valid module structure
        if not (path / "pyproject.toml").exists() and not (path / "setup.py").exists():
            raise ValueError(f"Invalid module structure at {path}: missing pyproject.toml or setup.py")

        module_info = ModuleInfo(
            id=module_id,
            name=name,
            category=category,  # type: ignore
            description=description or f"Local development module at {path}",
            source=str(path),
            installed=False,
        )

        self._local[module_id] = module_info
        logger.info(f"Registered local module: {module_id} at {path}")
        return module_info

    def unregister_local(self, module_id: str) -> bool:
        """
        Unregister a local development module.

        Args:
            module_id: Module identifier

        Returns:
            True if unregistered, False if not found
        """
        if module_id in self._local:
            del self._local[module_id]
            logger.info(f"Unregistered local module: {module_id}")
            return True
        return False

    def list_by_category(self, category: str) -> list[ModuleInfo]:
        """
        List all modules of a specific category.

        Args:
            category: Category to filter by (provider, tool, orchestrator, context, hook)

        Returns:
            List of matching modules
        """
        all_modules = self.list_all()
        return [m for m in all_modules if m.category == category]

    def list_all(self) -> list[ModuleInfo]:
        """
        List all modules (discovered + known + local), deduplicated by ID.

        Precedence: local > discovered > known
        """
        result: dict[str, ModuleInfo] = {}

        # Add known first (lowest precedence)
        for module_id, info in self._known.items():
            result[module_id] = info

        # Override with discovered (higher precedence)
        for module_id, info in self._discovered.items():
            result[module_id] = info

        # Override with local (highest precedence)
        for module_id, info in self._local.items():
            result[module_id] = info

        return sorted(result.values(), key=lambda m: (m.category, m.id))

    def get_info(self, module_id: str) -> ModuleInfo | None:
        """
        Get module info by ID.

        Args:
            module_id: Module identifier

        Returns:
            ModuleInfo if found, None otherwise
        """
        # Check in order of precedence
        if module_id in self._local:
            return self._local[module_id]
        if module_id in self._discovered:
            return self._discovered[module_id]
        if module_id in self._known:
            return self._known[module_id]
        return None

    # Alias for backwards compatibility
    get = get_info

    def is_installed(self, module_id: str) -> bool:
        """Check if a module is installed and available."""
        info = self.get(module_id)
        if info is None:
            return False
        return info.installed or module_id in self._discovered
