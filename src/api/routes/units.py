"""Unit routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies.database import get_db
from src.api.dependencies.roles import require_resident
from src.database.models.user import User
from src.models.api.units import UnitResponse
from src.repositories.unit_repository import UnitRepository

router = APIRouter()


@router.get("/my", response_model=list[UnitResponse])
def my_units(user: User = Depends(require_resident), db: Session = Depends(get_db)) -> list[UnitResponse]:
    units = UnitRepository(db).list_active_memberships_for_user(user.id)
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
