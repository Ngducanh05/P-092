"""Unit API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UnitResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    unit_id: UUID
    building_code: str
    floor: str
    unit_number: str
    is_active: bool
