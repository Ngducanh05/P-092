"""Role authorization dependencies."""

from fastapi import Depends

from src.api.dependencies.auth import get_current_user
from src.database.models.user import User
from src.models.api.errors import ROLE_FORBIDDEN, DomainError
from src.models.enums import Role


def require_role(*roles: Role):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise DomainError(ROLE_FORBIDDEN, "Role is not allowed for this operation.", 403)
        return user

    return dependency


def require_resident(user: User = Depends(require_role(Role.RESIDENT))) -> User:
    return user


def require_coordinator(user: User = Depends(require_role(Role.COORDINATOR))) -> User:
    return user


def require_technician(user: User = Depends(require_role(Role.TECHNICIAN))) -> User:
    return user
