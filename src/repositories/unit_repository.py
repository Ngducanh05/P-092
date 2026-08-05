"""Unit and membership queries."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models.unit import Unit
from src.database.models.user_unit_membership import UserUnitMembership


class UnitRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active_memberships_for_user(self, user_id: UUID) -> list[Unit]:
        return list(
            self.db.scalars(
                select(Unit)
                .join(UserUnitMembership, UserUnitMembership.unit_id == Unit.id)
                .where(
                    UserUnitMembership.user_id == user_id,
                    UserUnitMembership.is_active.is_(True),
                    Unit.is_active.is_(True),
                )
                .order_by(Unit.building_code, Unit.floor, Unit.unit_number)
            )
        )

    def get_authorized_unit_for_user(self, user_id: UUID, unit_id: UUID) -> Unit | None:
        return self.db.scalar(
            select(Unit)
            .join(UserUnitMembership, UserUnitMembership.unit_id == Unit.id)
            .where(
                Unit.id == unit_id,
                Unit.is_active.is_(True),
                UserUnitMembership.user_id == user_id,
                UserUnitMembership.is_active.is_(True),
            )
        )

    def count_active_units_for_user(self, user_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count(Unit.id))
                .join(UserUnitMembership, UserUnitMembership.unit_id == Unit.id)
                .where(
                    UserUnitMembership.user_id == user_id,
                    UserUnitMembership.is_active.is_(True),
                    Unit.is_active.is_(True),
                )
            )
            or 0
        )
