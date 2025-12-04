"""Core library for Amplifier Playground."""

from .collection_manager import CollectionInfo, CollectionManager
from .config_manager import ConfigManager, MountPlanConfig
from .credentials import (
    get_credential,
    get_credential_status,
    get_required_credentials_for_providers,
    load_credentials_to_env,
    set_credential,
    delete_credential,
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    OLLAMA_BASE_URL,
    VLLM_BASE_URL,
)
from .module_registry import ModuleInfo, ModuleRegistry
from .protocols import EventCallback
from .session_runner import SessionManager, SessionRunner
from .ux_systems import (
    PlaygroundApprovalSystem,
    PlaygroundDisplaySystem,
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
    # Credentials
    "get_credential",
    "get_credential_status",
    "get_required_credentials_for_providers",
    "load_credentials_to_env",
    "set_credential",
    "delete_credential",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "OLLAMA_BASE_URL",
    "VLLM_BASE_URL",
    # Modules
    "ModuleRegistry",
    "ModuleInfo",
    # Sessions
    "SessionRunner",
    "SessionManager",
    # Protocols
    "EventCallback",
    # UX Systems
    "PlaygroundApprovalSystem",
    "PlaygroundDisplaySystem",
    "create_cli_event_callback",
    "create_logging_event_callback",
]
