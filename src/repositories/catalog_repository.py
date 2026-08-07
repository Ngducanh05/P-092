"""Read-only product catalogs."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from src.database.models.category import CategoryCatalog
from src.database.models.location import Location


class CatalogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_locations(
        self, *, building_id: UUID | None = None, resident_unit_id: UUID | None = None
    ) -> list[Location]:
        query = select(Location).where(Location.is_active.is_(True))
        if building_id is not None:
            query = query.where(Location.building_id == building_id)
        if resident_unit_id is not None:
            # Resident dropdown may contain common-area locations plus locations
            # scoped to the authenticated unit, never another household's unit.
            query = query.where(or_(Location.unit_id.is_(None), Location.unit_id == resident_unit_id))
        return list(
            self.db.scalars(
                query
                .options(
                    joinedload(Location.building),
                    joinedload(Location.floor),
                    joinedload(Location.location_type),
                    joinedload(Location.unit),
                )
                .order_by(Location.building_id, Location.floor_id, Location.label)
            )
        )

    def get_location(self, location_id: UUID) -> Location | None:
        return self.db.scalar(
            select(Location)
            .where(Location.id == location_id, Location.is_active.is_(True))
            .options(joinedload(Location.building), joinedload(Location.floor), joinedload(Location.location_type), joinedload(Location.unit))
        )

    def list_categories(self) -> list[CategoryCatalog]:
        return list(self.db.scalars(select(CategoryCatalog).where(CategoryCatalog.is_active.is_(True)).order_by(CategoryCatalog.display_name)))

    def get_category(self, category_id: UUID) -> CategoryCatalog | None:
        return self.db.scalar(select(CategoryCatalog).where(CategoryCatalog.id == category_id, CategoryCatalog.is_active.is_(True)))
