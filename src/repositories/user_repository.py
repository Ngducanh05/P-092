"""User persistence operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models.user import User
from src.models.enums import Role


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_active_profile(self, user_id: UUID) -> User | None:
        return self.db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))

    def get_role(self, user_id: UUID) -> Role | None:
        return self.db.scalar(select(User.role).where(User.id == user_id, User.is_active.is_(True)))

    def create_resident_profile(self, user_id: UUID, email: str | None, phone_number: str | None) -> User:
        user = User(id=user_id, email=email, phone_number=phone_number, role=Role.RESIDENT, is_active=True)
        self.db.add(user)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            existing = self.get_by_id(user_id)
            if existing is None:
                raise
            return existing
        return user
