"""Credentials manager for storing API keys locally."""

import json
import os
import stat
from pathlib import Path
from typing import Any

# Supported credential keys
ANTHROPIC_API_KEY = "anthropic_api_key"
OPENAI_API_KEY = "openai_api_key"
AZURE_OPENAI_API_KEY = "azure_openai_api_key"
AZURE_OPENAI_ENDPOINT = "azure_openai_endpoint"
OLLAMA_BASE_URL = "ollama_base_url"
VLLM_BASE_URL = "vllm_base_url"

# Environment variable mappings
ENV_VAR_MAPPING = {
    ANTHROPIC_API_KEY: "ANTHROPIC_API_KEY",
    OPENAI_API_KEY: "OPENAI_API_KEY",
    AZURE_OPENAI_API_KEY: "AZURE_OPENAI_API_KEY",
    AZURE_OPENAI_ENDPOINT: "AZURE_OPENAI_ENDPOINT",
    OLLAMA_BASE_URL: "OLLAMA_BASE_URL",
    VLLM_BASE_URL: "VLLM_BASE_URL",
}


def get_credentials_path() -> Path:
    """Get the path to the credentials file."""
    return Path.home() / ".amplifier-playground" / "credentials.json"


def _ensure_directory(path: Path) -> None:
    """Ensure the parent directory exists with secure permissions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Set directory permissions to 700 (owner only)
    os.chmod(path.parent, stat.S_IRWXU)


def _load_credentials() -> dict[str, Any]:
    """Load credentials from file."""
    path = get_credentials_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_credentials(credentials: dict[str, Any]) -> None:
    """Save credentials to file with secure permissions."""
    path = get_credentials_path()
    _ensure_directory(path)

    with open(path, "w") as f:
        json.dump(credentials, f, indent=2)

    # Set file permissions to 600 (owner read/write only)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def get_credential(key: str) -> str | None:
    """
    Get a credential value.

    Checks environment variable first, then falls back to stored credentials.

    Args:
        key: Credential key (e.g., 'anthropic_api_key')

    Returns:
        The credential value or None if not found
    """
    # Check environment variable first
    env_var = ENV_VAR_MAPPING.get(key)
    if env_var:
        env_value = os.environ.get(env_var)
        if env_value:
            return env_value

    # Fall back to stored credentials
    credentials = _load_credentials()
    return credentials.get(key)


def set_credential(key: str, value: str) -> None:
    """
    Store a credential value and update environment variable.

    Args:
        key: Credential key (e.g., 'anthropic_api_key')
        value: The credential value to store
    """
    credentials = _load_credentials()
    credentials[key] = value
    _save_credentials(credentials)

    # Also set the environment variable immediately so it takes effect
    env_var = ENV_VAR_MAPPING.get(key)
    if env_var:
        os.environ[env_var] = value


def delete_credential(key: str) -> bool:
    """
    Delete a stored credential and remove from environment.

    Args:
        key: Credential key to delete

    Returns:
        True if deleted, False if not found
    """
    credentials = _load_credentials()
    if key in credentials:
        del credentials[key]
        _save_credentials(credentials)

        # Also remove from environment
        env_var = ENV_VAR_MAPPING.get(key)
        if env_var and env_var in os.environ:
            del os.environ[env_var]

        return True
    return False


def get_credential_status() -> dict[str, dict[str, Any]]:
    """
    Get status of all known credentials.

    Returns:
        Dict mapping credential keys to their status:
        {
            "anthropic_api_key": {
                "configured": True,
                "source": "env" | "file" | None,
                "masked_value": "sk-ant-***..."
            }
        }
    """
    status = {}

    for key, env_var in ENV_VAR_MAPPING.items():
        env_value = os.environ.get(env_var)
        stored_credentials = _load_credentials()
        stored_value = stored_credentials.get(key)

        if env_value:
            status[key] = {
                "configured": True,
                "source": "env",
                "masked_value": _mask_key(env_value),
            }
        elif stored_value:
            status[key] = {
                "configured": True,
                "source": "file",
                "masked_value": _mask_key(stored_value),
            }
        else:
            status[key] = {
                "configured": False,
                "source": None,
                "masked_value": None,
            }

    return status


def load_credentials_to_env() -> dict[str, str]:
    """
    Load stored credentials into environment variables.

    Only sets env vars that aren't already set.
    Call this on startup to make stored credentials available to modules.

    Returns:
        Dict of env vars that were set
    """
    set_vars = {}
    credentials = _load_credentials()

    for key, env_var in ENV_VAR_MAPPING.items():
        # Skip if env var already set
        if os.environ.get(env_var):
            continue

        # Set from stored credentials if available
        stored_value = credentials.get(key)
        if stored_value:
            os.environ[env_var] = stored_value
            set_vars[env_var] = _mask_key(stored_value)

    return set_vars


def _mask_key(value: str) -> str:
    """Mask an API key for display, showing only first and last few chars."""
    if len(value) <= 12:
        return "***"
    return f"{value[:7]}...{value[-4:]}"


# Provider module to credential key mapping
# Maps provider module names to the list of credential keys they require
PROVIDER_CREDENTIAL_MAPPING: dict[str, list[str]] = {
    "amplifier-module-provider-anthropic": [ANTHROPIC_API_KEY],
    "provider-anthropic": [ANTHROPIC_API_KEY],
    "anthropic": [ANTHROPIC_API_KEY],
    "amplifier-module-provider-openai": [OPENAI_API_KEY],
    "provider-openai": [OPENAI_API_KEY],
    "openai": [OPENAI_API_KEY],
    "amplifier-module-provider-azure-openai": [AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT],
    "provider-azure-openai": [AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT],
    "azure-openai": [AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT],
    "amplifier-module-provider-ollama": [OLLAMA_BASE_URL],
    "provider-ollama": [OLLAMA_BASE_URL],
    "ollama": [OLLAMA_BASE_URL],
    "amplifier-module-provider-vllm": [VLLM_BASE_URL],
    "provider-vllm": [VLLM_BASE_URL],
    "vllm": [VLLM_BASE_URL],
}

# Display names for credentials
CREDENTIAL_DISPLAY_NAMES = {
    ANTHROPIC_API_KEY: "Anthropic API Key",
    OPENAI_API_KEY: "OpenAI API Key",
    AZURE_OPENAI_API_KEY: "Azure OpenAI API Key",
    AZURE_OPENAI_ENDPOINT: "Azure OpenAI Endpoint",
    OLLAMA_BASE_URL: "Ollama Base URL",
    VLLM_BASE_URL: "vLLM Base URL",
}


def get_required_credentials_for_providers(provider_modules: list[str]) -> list[dict[str, Any]]:
    """
    Get required credentials for a list of provider modules.

    Args:
        provider_modules: List of provider module names from mount plan

    Returns:
        List of credential requirements with status:
        [
            {
                "provider": "anthropic",
                "credential_key": "anthropic_api_key",
                "env_var": "ANTHROPIC_API_KEY",
                "configured": True/False,
                "display_name": "Anthropic API Key"
            }
        ]
    """
    requirements = []
    seen_keys = set()
    status = get_credential_status()

    for module in provider_modules:
        # Normalize module name (strip git URLs, get base name)
        module_name = module.split("/")[-1].replace(".git", "")

        credential_keys = PROVIDER_CREDENTIAL_MAPPING.get(module_name, [])
        for credential_key in credential_keys:
            if credential_key not in seen_keys:
                seen_keys.add(credential_key)
                cred_status = status.get(credential_key, {})
                requirements.append({
                    "provider": module_name,
                    "credential_key": credential_key,
                    "env_var": ENV_VAR_MAPPING.get(credential_key),
                    "configured": cred_status.get("configured", False),
                    "display_name": CREDENTIAL_DISPLAY_NAMES.get(credential_key, credential_key),
                })

    return requirements
