"""Auth API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.models.api.units import UnitResponse
from src.models.enums import Role


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    role: Role
    email: str | None
    phone_number: str | None
    full_name: str | None
    is_active: bool
    active_unit_memberships: list[UnitResponse]
