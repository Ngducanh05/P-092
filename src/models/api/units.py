"""Unit API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UnitResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        json_schema_extra={
            "example": {
                "unit_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "building_code": "A",
                "floor": "10",
                "unit_number": "1002",
                "is_active": True,
            }
        },
    )

    unit_id: UUID = Field(description="Application UUID for the building unit.")
    building_code: str = Field(description="Building or tower code visible to residents and BQL staff.")
    floor: str = Field(description="Floor label for the unit.")
    unit_number: str = Field(description="Unit or apartment number.")
    is_active: bool = Field(description="Whether the unit is active and can be used for resident ticket access.")
