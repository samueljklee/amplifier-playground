"""Settings routes for managing API keys and configuration."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from amplifier_playground.core import (
    get_credential_status,
    set_credential,
    delete_credential,
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
)

router = APIRouter(prefix="/settings", tags=["settings"])


class CredentialStatus(BaseModel):
    """Status of a single credential."""

    configured: bool
    source: str | None  # "env", "file", or None
    masked_value: str | None


class CredentialsStatusResponse(BaseModel):
    """Response containing status of all credentials."""

    anthropic_api_key: CredentialStatus
    openai_api_key: CredentialStatus


class SetCredentialRequest(BaseModel):
    """Request to set a credential."""

    value: str


@router.get("/credentials", response_model=CredentialsStatusResponse)
async def get_credentials_status() -> CredentialsStatusResponse:
    """Get the configuration status of all API keys."""
    status = get_credential_status()

    return CredentialsStatusResponse(
        anthropic_api_key=CredentialStatus(**status.get(ANTHROPIC_API_KEY, {
            "configured": False,
            "source": None,
            "masked_value": None,
        })),
        openai_api_key=CredentialStatus(**status.get(OPENAI_API_KEY, {
            "configured": False,
            "source": None,
            "masked_value": None,
        })),
    )


@router.put("/credentials/anthropic")
async def set_anthropic_key(request: SetCredentialRequest) -> dict:
    """Set the Anthropic API key."""
    if not request.value or not request.value.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    value = request.value.strip()

    # Basic validation - Anthropic keys start with "sk-ant-"
    if not value.startswith("sk-ant-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid Anthropic API key format. Keys should start with 'sk-ant-'"
        )

    set_credential(ANTHROPIC_API_KEY, value)

    return {"status": "saved", "key": "anthropic_api_key"}


@router.delete("/credentials/anthropic")
async def delete_anthropic_key() -> dict:
    """Delete the stored Anthropic API key."""
    deleted = delete_credential(ANTHROPIC_API_KEY)

    if not deleted:
        raise HTTPException(status_code=404, detail="No stored Anthropic API key found")

    return {"status": "deleted", "key": "anthropic_api_key"}


@router.put("/credentials/openai")
async def set_openai_key(request: SetCredentialRequest) -> dict:
    """Set the OpenAI API key."""
    if not request.value or not request.value.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")

    value = request.value.strip()

    # Basic validation - OpenAI keys start with "sk-"
    if not value.startswith("sk-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid OpenAI API key format. Keys should start with 'sk-'"
        )

    set_credential(OPENAI_API_KEY, value)

    return {"status": "saved", "key": "openai_api_key"}


@router.delete("/credentials/openai")
async def delete_openai_key() -> dict:
    """Delete the stored OpenAI API key."""
    deleted = delete_credential(OPENAI_API_KEY)

    if not deleted:
        raise HTTPException(status_code=404, detail="No stored OpenAI API key found")

    return {"status": "deleted", "key": "openai_api_key"}
