"""Settings routes for managing API keys and configuration."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from amplifier_playground.core import (
    get_credential_status,
    set_credential,
    delete_credential,
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    OLLAMA_BASE_URL,
    VLLM_BASE_URL,
)
from amplifier_playground.core.credentials import ENV_VAR_MAPPING, CREDENTIAL_DISPLAY_NAMES

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


class CredentialsListResponse(BaseModel):
    """Response containing all credentials as a list."""

    credentials: list[CredentialInfo]


class SetCredentialRequest(BaseModel):
    """Request to set a credential by key."""

    value: str


class SetGenericCredentialRequest(BaseModel):
    """Request to set a credential with custom env var."""

    env_var: str
    value: str


@router.get("/credentials", response_model=CredentialsListResponse)
async def get_credentials_status_list() -> CredentialsListResponse:
    """Get the configuration status of all known credentials."""
    status = get_credential_status()

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

    return CredentialsListResponse(credentials=credentials)


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
