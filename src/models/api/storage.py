"""Storage API schemas."""

from pydantic import BaseModel, ConfigDict, Field


class SignedUploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0)


class SignedUploadResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage_path: str
    signed_upload_url: str | None = None
    signed_upload_token: str | None = None
    expires_in: int
    required_headers: dict[str, str] = Field(default_factory=dict)
