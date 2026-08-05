"""Small auth response helpers."""

from src.database.models.unit import Unit
from src.database.models.user import User
from src.models.api.auth import CurrentUserResponse
from src.models.api.units import UnitResponse


def current_user_response(user: User, active_units: list[Unit]) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        role=user.role,
        email=user.email,
        phone_number=user.phone_number,
        full_name=user.full_name,
        is_active=user.is_active,
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
