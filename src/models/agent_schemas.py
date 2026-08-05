from pydantic import BaseModel, ConfigDict, Field

from src.models.enums import Category, Severity


class AgentResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    category: Category = Field(..., description="Primary issue category selected by the agent.")
    severity: Severity = Field(..., description="Severity level selected by the agent.")
    summary: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Short normalized summary of the reported issue.",
    )
    red_flags: list[str] = Field(
        default_factory=list,
        description="Safety or urgency indicators detected in the report.",
    )
    text_categories: list[Category] = Field(
        default_factory=list,
        description="Issue categories inferred from text content.",
    )
    image_category: Category | None = Field(
        default=None,
        description="Issue category inferred from image content, when available.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent confidence score from 0.0 to 1.0.",
    )
    recommended_department: str | None = Field(
        default=None,
        max_length=100,
        description="Suggested department for handling the ticket.",
    )
