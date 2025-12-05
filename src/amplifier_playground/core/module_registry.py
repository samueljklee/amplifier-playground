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
    config: dict | None = None  # User-provided configuration for the module


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
        """Initialize curated list of known modules from the Amplifier module catalog."""
        # All modules from MODULES.md - reference implementations
        known = [
            # === ORCHESTRATORS ===
            ModuleInfo(
                id="loop-basic",
                name="Basic Loop Orchestrator",
                category="orchestrator",
                description="Standard sequential execution - simple request/response flow",
                source="git+https://github.com/microsoft/amplifier-module-loop-basic@main",
            ),
            ModuleInfo(
                id="loop-streaming",
                name="Streaming Loop Orchestrator",
                category="orchestrator",
                description="Real-time streaming responses with extended thinking support",
                source="git+https://github.com/microsoft/amplifier-module-loop-streaming@main",
            ),
            ModuleInfo(
                id="loop-events",
                name="Event-Driven Orchestrator",
                category="orchestrator",
                description="Event-driven orchestrator with hook integration",
                source="git+https://github.com/microsoft/amplifier-module-loop-events@main",
            ),
            # === PROVIDERS ===
            ModuleInfo(
                id="provider-anthropic",
                name="Anthropic Provider",
                category="provider",
                description="Anthropic Claude integration (Sonnet 4.5, Opus, etc.)",
                source="git+https://github.com/microsoft/amplifier-module-provider-anthropic@main",
            ),
            ModuleInfo(
                id="provider-openai",
                name="OpenAI Provider",
                category="provider",
                description="OpenAI GPT integration",
                source="git+https://github.com/microsoft/amplifier-module-provider-openai@main",
            ),
            ModuleInfo(
                id="provider-azure-openai",
                name="Azure OpenAI Provider",
                category="provider",
                description="Azure OpenAI with managed identity support",
                source="git+https://github.com/microsoft/amplifier-module-provider-azure-openai@main",
            ),
            ModuleInfo(
                id="provider-ollama",
                name="Ollama Provider",
                category="provider",
                description="Local Ollama models",
                source="git+https://github.com/microsoft/amplifier-module-provider-ollama@main",
            ),
            ModuleInfo(
                id="provider-mock",
                name="Mock Provider",
                category="provider",
                description="Mock provider for testing",
                source="git+https://github.com/microsoft/amplifier-module-provider-mock@main",
            ),
            # === TOOLS ===
            ModuleInfo(
                id="tool-filesystem",
                name="Filesystem Tool",
                category="tool",
                description="File operations (read, write, edit, list)",
                source="git+https://github.com/microsoft/amplifier-module-tool-filesystem@main",
            ),
            ModuleInfo(
                id="tool-bash",
                name="Bash Tool",
                category="tool",
                description="Shell command execution",
                source="git+https://github.com/microsoft/amplifier-module-tool-bash@main",
            ),
            ModuleInfo(
                id="tool-web",
                name="Web Tool",
                category="tool",
                description="Web search and content fetching",
                source="git+https://github.com/microsoft/amplifier-module-tool-web@main",
            ),
            ModuleInfo(
                id="tool-search",
                name="Search Tool",
                category="tool",
                description="Web search capabilities",
                source="git+https://github.com/microsoft/amplifier-module-tool-search@main",
            ),
            ModuleInfo(
                id="tool-task",
                name="Task Tool",
                category="tool",
                description="Agent delegation (sub-session spawning)",
                source="git+https://github.com/microsoft/amplifier-module-tool-task@main",
            ),
            # === CONTEXT MANAGERS ===
            ModuleInfo(
                id="context-simple",
                name="Simple Context Manager",
                category="context",
                description="In-memory context with automatic compaction",
                source="git+https://github.com/microsoft/amplifier-module-context-simple@main",
            ),
            ModuleInfo(
                id="context-persistent",
                name="Persistent Context Manager",
                category="context",
                description="File-backed persistent context across sessions",
                source="git+https://github.com/microsoft/amplifier-module-context-persistent@main",
            ),
            # === HOOKS ===
            ModuleInfo(
                id="hooks-logging",
                name="Logging Hooks",
                category="hook",
                description="Unified JSONL event logging to per-session files",
                source="git+https://github.com/microsoft/amplifier-module-hooks-logging@main",
            ),
            ModuleInfo(
                id="hooks-redaction",
                name="Redaction Hooks",
                category="hook",
                description="Privacy-preserving data redaction",
                source="git+https://github.com/microsoft/amplifier-module-hooks-redaction@main",
            ),
            ModuleInfo(
                id="hooks-approval",
                name="Approval Hooks",
                category="hook",
                description="Interactive approval for sensitive operations",
                source="git+https://github.com/microsoft/amplifier-module-hooks-approval@main",
            ),
            ModuleInfo(
                id="hooks-backup",
                name="Backup Hooks",
                category="hook",
                description="Automatic session backup",
                source="git+https://github.com/microsoft/amplifier-module-hooks-backup@main",
            ),
            ModuleInfo(
                id="hooks-streaming-ui",
                name="Streaming UI Hooks",
                category="hook",
                description="Real-time UI updates during streaming",
                source="git+https://github.com/microsoft/amplifier-module-hooks-streaming-ui@main",
            ),
            ModuleInfo(
                id="hooks-scheduler-cost-aware",
                name="Cost-Aware Scheduler",
                category="hook",
                description="Cost-aware model routing",
                source="git+https://github.com/microsoft/amplifier-module-hooks-scheduler-cost-aware@main",
            ),
            ModuleInfo(
                id="hooks-scheduler-heuristic",
                name="Heuristic Scheduler",
                category="hook",
                description="Heuristic-based model selection",
                source="git+https://github.com/microsoft/amplifier-module-hooks-scheduler-heuristic@main",
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

    def add_custom(
        self,
        module_id: str,
        name: str,
        category: str,
        source: str,
        description: str | None = None,
        config: dict | None = None,
    ) -> ModuleInfo:
        """
        Add a custom module with git URL or path source.

        This allows users to add custom providers, tools, hooks, etc.
        that are not in the known catalog.

        Args:
            module_id: Unique module identifier (e.g., "my-custom-provider")
            name: Display name for the module
            category: Module category (provider, tool, orchestrator, context, hook)
            source: Git URL (e.g., "git+https://github.com/user/repo@main") or local path
            description: Optional description of the module
            config: Optional key-value configuration for the module

        Returns:
            Created ModuleInfo

        Raises:
            ValueError: If category is invalid
        """
        valid_categories = ["provider", "tool", "orchestrator", "context", "hook"]
        if category not in valid_categories:
            raise ValueError(f"Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}")

        module_info = ModuleInfo(
            id=module_id,
            name=name,
            category=category,  # type: ignore
            description=description or f"Custom {category} module",
            source=source,
            installed=False,
            config=config,
        )

        self._local[module_id] = module_info
        logger.info(f"Added custom module: {module_id} ({category}) from {source}")
        return module_info

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
