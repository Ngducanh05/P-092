"""Small auth response helpers."""

from src.database.models.bql_staff import BQLStaff
from src.database.models.resident import Resident
from src.database.models.unit import Unit
from src.models.api.auth import CurrentBQLResponse, CurrentResidentResponse
from src.models.api.units import UnitResponse


def current_resident_response(resident: Resident, active_units: list[Unit]) -> CurrentResidentResponse:
    return CurrentResidentResponse(
        actor_type="resident",
        id=resident.id,
        phone_number=resident.phone_number,
        full_name=resident.full_name,
        is_active=resident.is_active,
        active_unit_memberships=[
            UnitResponse(
                unit_id=unit.id,
                building_code=unit.building_code,
                floor=unit.floor,
                unit_number=unit.unit_number,
                is_active=unit.is_active,
            )
            for unit in active_units
        ],
    )


def current_bql_response(bql_staff: BQLStaff) -> CurrentBQLResponse:
    return CurrentBQLResponse(
        actor_type="bql",
        id=bql_staff.id,
        email=bql_staff.email,
        full_name=bql_staff.full_name,
        is_active=bql_staff.is_active,
    )
