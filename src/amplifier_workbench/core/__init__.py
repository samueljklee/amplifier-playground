"""Core library for Amplifier Workbench."""

from .collection_manager import CollectionInfo, CollectionManager
from .config_manager import ConfigManager, MountPlanConfig
from .module_registry import ModuleInfo, ModuleRegistry
from .protocols import EventCallback
from .session_runner import SessionManager, SessionRunner
from .ux_systems import (
    WorkbenchApprovalSystem,
    WorkbenchDisplaySystem,
    create_cli_event_callback,
    create_logging_event_callback,
)

__all__ = [
    # Collections
    "CollectionManager",
    "CollectionInfo",
    # Config
    "ConfigManager",
    "MountPlanConfig",
    # Modules
    "ModuleRegistry",
    "ModuleInfo",
    # Sessions
    "SessionRunner",
    "SessionManager",
    # Protocols
    "EventCallback",
    # UX Systems
    "WorkbenchApprovalSystem",
    "WorkbenchDisplaySystem",
    "create_cli_event_callback",
    "create_logging_event_callback",
]
