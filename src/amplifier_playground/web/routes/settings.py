"""Settings routes for managing API keys and configuration."""

import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from amplifier_playground.core import (
    get_credential_status,
    set_credential,
    delete_credential,
    get_custom_credentials,
    add_custom_credential,
    delete_custom_credential,
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    OLLAMA_BASE_URL,
    VLLM_BASE_URL,
)
from amplifier_playground.core.credentials import ENV_VAR_MAPPING, CREDENTIAL_DISPLAY_NAMES, _mask_key

router = APIRouter(prefix="/settings", tags=["settings"])


class CredentialStatus(BaseModel):
    """Status of a single credential."""

    configured: bool
    source: str | None  # "env", "file", or None
    masked_value: str | None


class CredentialInfo(BaseModel):
    """Information about a credential including its status."""

    key: str
    env_var: str
    display_name: str
    configured: bool
    source: str | None
    masked_value: str | None


class CustomCredentialInfo(BaseModel):
    """Information about a custom (user-defined) credential."""

    env_var: str
    masked_value: str
    is_custom: bool = True


class CredentialsListResponse(BaseModel):
    """Response containing all credentials as a list."""

    credentials: list[CredentialInfo]
    custom_credentials: list[CustomCredentialInfo]


class SetCredentialRequest(BaseModel):
    """Request to set a credential by key."""

    value: str


class SetCustomCredentialRequest(BaseModel):
    """Request to add or update a custom credential."""

    env_var: str
    value: str


@router.get("/credentials", response_model=CredentialsListResponse)
async def get_credentials_status_list() -> CredentialsListResponse:
    """Get the configuration status of all known and custom credentials."""
    status = get_credential_status()

    # Known credentials
    credentials = []
    for key, env_var in ENV_VAR_MAPPING.items():
        cred_status = status.get(key, {"configured": False, "source": None, "masked_value": None})
        credentials.append(CredentialInfo(
            key=key,
            env_var=env_var,
            display_name=CREDENTIAL_DISPLAY_NAMES.get(key, key),
            configured=cred_status.get("configured", False),
            source=cred_status.get("source"),
            masked_value=cred_status.get("masked_value"),
        ))

    # Custom credentials
    custom_creds = get_custom_credentials()
    custom_credentials = [
        CustomCredentialInfo(
            env_var=cred["env_var"],
            masked_value=_mask_key(cred["value"]),
        )
        for cred in custom_creds
    ]

    return CredentialsListResponse(credentials=credentials, custom_credentials=custom_credentials)


@router.put("/credentials/{credential_key}")
async def set_credential_by_key(credential_key: str, request: SetCredentialRequest) -> dict:
    """Set a credential by its internal key."""
    if not request.value or not request.value.strip():
        raise HTTPException(status_code=400, detail="Value cannot be empty")

    # Check if this is a known credential key
    if credential_key not in ENV_VAR_MAPPING:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown credential key: {credential_key}. Use POST /credentials/custom for custom env vars."
        )

    value = request.value.strip()

    # Apply validation based on credential type
    if credential_key == ANTHROPIC_API_KEY:
        if not value.startswith("sk-ant-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid Anthropic API key format. Keys should start with 'sk-ant-'"
            )
    elif credential_key == OPENAI_API_KEY:
        if not value.startswith("sk-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid OpenAI API key format. Keys should start with 'sk-'"
            )
    elif credential_key == AZURE_OPENAI_ENDPOINT:
        if not value.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="Invalid Azure OpenAI endpoint. Should be a URL starting with 'https://'"
            )
    elif credential_key in [OLLAMA_BASE_URL, VLLM_BASE_URL]:
        if not value.startswith("http://") and not value.startswith("https://"):
            raise HTTPException(
                status_code=400,
                detail="Invalid URL. Should start with 'http://' or 'https://'"
            )

    set_credential(credential_key, value)

    return {"status": "saved", "key": credential_key, "env_var": ENV_VAR_MAPPING.get(credential_key)}


@router.delete("/credentials/{credential_key}")
async def delete_credential_by_key(credential_key: str) -> dict:
    """Delete a stored credential by its internal key."""
    if credential_key not in ENV_VAR_MAPPING:
        raise HTTPException(status_code=400, detail=f"Unknown credential key: {credential_key}")

    deleted = delete_credential(credential_key)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"No stored credential found for {credential_key}")

    return {"status": "deleted", "key": credential_key}


# Legacy routes for backwards compatibility
@router.put("/credentials/anthropic")
async def set_anthropic_key(request: SetCredentialRequest) -> dict:
    """Set the Anthropic API key (legacy route)."""
    return await set_credential_by_key(ANTHROPIC_API_KEY, request)


@router.delete("/credentials/anthropic")
async def delete_anthropic_key() -> dict:
    """Delete the stored Anthropic API key (legacy route)."""
    return await delete_credential_by_key(ANTHROPIC_API_KEY)


@router.put("/credentials/openai")
async def set_openai_key(request: SetCredentialRequest) -> dict:
    """Set the OpenAI API key (legacy route)."""
    return await set_credential_by_key(OPENAI_API_KEY, request)


@router.delete("/credentials/openai")
async def delete_openai_key() -> dict:
    """Delete the stored OpenAI API key (legacy route)."""
    return await delete_credential_by_key(OPENAI_API_KEY)


# Custom credentials routes
@router.post("/credentials/custom")
async def add_custom_credential_route(request: SetCustomCredentialRequest) -> dict:
    """Add or update a custom credential with user-defined env var name."""
    env_var = request.env_var.strip()
    value = request.value.strip()

    if not env_var:
        raise HTTPException(status_code=400, detail="Environment variable name cannot be empty")
    if not value:
        raise HTTPException(status_code=400, detail="Value cannot be empty")

    # Validate env var format (uppercase letters, numbers, underscores)
    if not re.match(r"^[A-Z][A-Z0-9_]*$", env_var):
        raise HTTPException(
            status_code=400,
            detail="Environment variable name must start with uppercase letter and contain only uppercase letters, numbers, and underscores"
        )

    # Don't allow overriding known credentials via custom route
    if env_var in ENV_VAR_MAPPING.values():
        raise HTTPException(
            status_code=400,
            detail=f"'{env_var}' is a known credential. Use the standard credentials endpoint instead."
        )

    add_custom_credential(env_var, value)
    return {"status": "saved", "env_var": env_var}


@router.delete("/credentials/custom/{env_var}")
async def delete_custom_credential_route(env_var: str) -> dict:
    """Delete a custom credential by its environment variable name."""
    deleted = delete_custom_credential(env_var)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"No custom credential found for {env_var}")

    return {"status": "deleted", "env_var": env_var}
