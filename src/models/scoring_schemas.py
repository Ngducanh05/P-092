from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.models.enums import Priority


class ScoringResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    severity_score: float = Field(..., ge=0.0, le=40.0, description="Severity contribution to the total score.")
    red_flag_score: float = Field(..., ge=0.0, le=30.0, description="Red-flag contribution to the total score.")
    impact_score: float = Field(..., ge=0.0, le=15.0, description="Impact contribution to the total score.")
    density_score: float = Field(..., ge=0.0, le=10.0, description="Issue density contribution to the total score.")
    age_score: float = Field(..., ge=0.0, le=5.0, description="Ticket age contribution to the total score.")
    total_score: float = Field(..., ge=0.0, le=100.0, description="Submitted total score for all scoring components.")
    priority: Priority = Field(..., description="Priority label assigned for the score.")
    scoring_reasons: list[str] = Field(
        default_factory=list,
        description="Human-readable reasons that explain the scoring result.",
    )

    @model_validator(mode="after")
    def validate_total_score(self) -> Self:
        expected_total = (
            self.severity_score
            + self.red_flag_score
            + self.impact_score
            + self.density_score
            + self.age_score
        )
        tolerance = 1e-6
        if abs(self.total_score - expected_total) > tolerance:
            msg = f"total_score must equal the sum of component scores ({expected_total})."
            raise ValueError(msg)
        return self
