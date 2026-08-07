"""Auth API schemas."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.models.api.units import UnitResponse


class CurrentResidentResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "actor_type": "resident",
                "id": "11111111-1111-4111-8111-111111111111",
                "phone_number": "+84901234567",
                "full_name": "Nguyen Van A",
                "is_active": True,
                "active_unit_memberships": [
                    {
                        "unit_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "building_code": "A",
                        "floor": "10",
                        "unit_number": "1002",
                        "is_active": True,
                    }
                ],
            }
        },
    )

    actor_type: Literal["resident"] = Field(description="Backend-derived actor type.")
    id: UUID = Field(description="Resident UUID, matching the Supabase Auth subject.")
    phone_number: str = Field(description="Verified E.164 phone number from the resident profile.")
    full_name: str | None = Field(description="Optional display name stored in the application profile.")
    is_active: bool = Field(description="Whether the application profile is active.")
    active_unit_memberships: list[UnitResponse] = Field(
        description="Active unit memberships used to authorize resident ticket access."
    )


class CurrentBQLResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "actor_type": "bql",
                "id": "22222222-2222-4222-8222-222222222222",
                "email": "bql@example.invalid",
                "full_name": "BQL Staff",
                "is_active": True,
            }
        },
    )

    actor_type: Literal["bql"] = Field(description="Backend-derived actor type.")
    id: UUID = Field(description="BQL staff UUID, matching the Supabase Auth subject.")
    email: str = Field(description="Verified email from the BQL staff profile.")
    full_name: str | None = Field(description="Optional display name stored in the application profile.")
    is_active: bool = Field(description="Whether the BQL staff profile is active.")


class CurrentTechnicianResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "actor_type": "technician",
                "id": "33333333-3333-4333-8333-333333333333",
                "email": "tech@example.invalid",
                "full_name": "Nguyen Van Tech",
                "phone_number": "+84901234567",
                "is_active": True,
                "is_available": True,
            }
        },
    )

    actor_type: Literal["technician"] = Field(description="Backend-derived actor type.")
    id: UUID = Field(description="Technician UUID, matching the Supabase Auth subject.")
    email: str = Field(description="Verified email from the technician profile.")
    full_name: str | None = Field(description="Optional display name stored in the technician profile.")
    phone_number: str | None = Field(description="Optional E.164 phone number from the technician profile.")
    is_active: bool = Field(description="Whether the technician profile is active.")
    is_available: bool = Field(description="Whether the technician is currently available for new assignments.")


CurrentActorResponse = CurrentResidentResponse | CurrentBQLResponse | CurrentTechnicianResponse
