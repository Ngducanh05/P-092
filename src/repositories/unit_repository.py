"""Unit and membership queries."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models.resident_unit_membership import ResidentUnitMembership
from src.database.models.unit import Unit


class UnitRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_active_memberships_for_resident(self, resident_id: UUID) -> list[Unit]:
        return list(
            self.db.scalars(
                select(Unit)
                .join(ResidentUnitMembership, ResidentUnitMembership.unit_id == Unit.id)
                .where(
                    ResidentUnitMembership.resident_id == resident_id,
                    ResidentUnitMembership.is_active.is_(True),
                    Unit.is_active.is_(True),
                )
                .order_by(Unit.building_code, Unit.floor, Unit.unit_number)
            )
        )

    def get_authorized_unit_for_resident(self, resident_id: UUID, unit_id: UUID) -> Unit | None:
        return self.db.scalar(
            select(Unit)
            .join(ResidentUnitMembership, ResidentUnitMembership.unit_id == Unit.id)
            .where(
                Unit.id == unit_id,
                Unit.is_active.is_(True),
                ResidentUnitMembership.resident_id == resident_id,
                ResidentUnitMembership.is_active.is_(True),
            )
        )

    def count_active_units_for_resident(self, resident_id: UUID) -> int:
        return int(
            self.db.scalar(
                select(func.count(Unit.id))
                .join(ResidentUnitMembership, ResidentUnitMembership.unit_id == Unit.id)
                .where(
                    ResidentUnitMembership.resident_id == resident_id,
                    ResidentUnitMembership.is_active.is_(True),
                    Unit.is_active.is_(True),
                )
            )
            or 0
        )
