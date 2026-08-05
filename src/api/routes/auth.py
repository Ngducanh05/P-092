"""Auth routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.dependencies.auth import get_current_user
from src.api.dependencies.database import get_db
from src.database.models.user import User
from src.models.api.auth import CurrentUserResponse
from src.repositories.unit_repository import UnitRepository
from src.services.auth_service import current_user_response

router = APIRouter()


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> CurrentUserResponse:
    units = UnitRepository(db).list_active_memberships_for_user(user.id)
    return current_user_response(user, units)
