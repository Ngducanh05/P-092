"""Resident and BQL profile persistence operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models.bql_staff import BQLStaff
from src.database.models.resident import Resident


class ProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_resident(self, auth_user_id: UUID) -> Resident | None:
        return self.db.get(Resident, auth_user_id)

    def get_bql_staff(self, auth_user_id: UUID) -> BQLStaff | None:
        return self.db.get(BQLStaff, auth_user_id)

    def get_resident_by_phone(self, phone_number: str) -> Resident | None:
        return self.db.scalar(select(Resident).where(Resident.phone_number == phone_number))

    def get_bql_by_email(self, email: str) -> BQLStaff | None:
        return self.db.scalar(select(BQLStaff).where(BQLStaff.email == email))

    def create_resident_profile(self, auth_user_id: UUID, phone_number: str) -> Resident:
        existing = self.get_resident(auth_user_id)
        if existing is not None:
            return existing
        resident = Resident(id=auth_user_id, phone_number=phone_number, is_active=True)
        try:
            with self.db.begin_nested():
                self.db.add(resident)
                self.db.flush()
        except IntegrityError:
            raise
        return resident
