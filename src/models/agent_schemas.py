"""Official Backend ↔ AI Agent contract from Self_Dev_Docs v2."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import Category, Severity


class AgentImageRef(BaseModel):
    """Private image reference passed from Backend/worker to the Agent."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    storage_bucket: str = Field(min_length=1, max_length=255)
    object_path: str = Field(min_length=1, max_length=2048)


class AgentAnalyzeRequest(BaseModel):
    """Official Self Dev request contract for the internal analyze boundary."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ticket_id: UUID
    text: str | None = Field(default=None, max_length=5000)
    image: AgentImageRef | None = None
    rule_version_id: UUID

class AgentResult(BaseModel):
    """Only fields produced by the AI layer.

    Category matching, score components, total score, Priority and ceiling are
    intentionally absent: Self Dev requires the Backend to calculate them.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text_categories: list[Category] = Field(default_factory=list)
    red_flag_text: bool = False
    image_categories: list[Category] | None = None
    red_flag_signal: bool = False
    severity: Severity
    severity_source: Literal["VISION", "TEXT_FALLBACK"]
    text_model_version: str = Field(min_length=1, max_length=100)
    vision_model_version: str | None = Field(default=None, max_length=100)
    error_code: str | None = Field(default=None, max_length=100)
