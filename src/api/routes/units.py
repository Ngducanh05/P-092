"""Unit routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_resident
from src.api.openapi_responses import AUTHENTICATED_RESPONSES
from src.database.models.resident import Resident
from src.models.api.units import UnitResponse
from src.repositories.unit_repository import UnitRepository

router = APIRouter()


@router.get(
    "/my",
    response_model=list[UnitResponse],
    summary="List my active units",
    description=(
        "Resident-only endpoint. Returns active unit memberships for the authenticated resident. These memberships "
        "control which tickets the resident can create and read."
    ),
    operation_id="list_my_units",
    responses=AUTHENTICATED_RESPONSES,
)
def my_units(resident: Resident = Depends(require_resident), db: Session = Depends(get_db)) -> list[UnitResponse]:
    units = UnitRepository(db).list_active_memberships_for_resident(resident.id)
    return [
        UnitResponse(
            unit_id=unit.id,
            building_code=unit.building_code,
            floor=unit.floor,
            unit_number=unit.unit_number,
            is_active=unit.is_active,
        )
        for unit in units
    ]
