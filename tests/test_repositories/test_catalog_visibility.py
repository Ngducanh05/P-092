from src.database.models.building import Building
from src.database.models.floor import Floor
from src.database.models.location import Location
from src.database.models.location_type import LocationType
from src.database.models.unit import Unit
from src.repositories.catalog_repository import CatalogRepository


def test_resident_location_catalog_hides_other_units(db_session):
    building = Building(code="A", name="Tòa A")
    floor = Floor(building=building, floor_code="10", display_name="Tầng 10", adjacency_index=10)
    own_unit = Unit(building=building, floor=floor, unit_code="A-1001")
    other_unit = Unit(building=building, floor=floor, unit_code="A-1002")
    common_type = LocationType(code="CORRIDOR", display_name="Hành lang")
    private_type = LocationType(code="INSIDE_UNIT", display_name="Trong căn hộ")
    common = Location(
        building=building,
        floor=floor,
        location_type=common_type,
        unit=None,
        label="Hành lang tầng 10",
    )
    own = Location(
        building=building,
        floor=floor,
        location_type=private_type,
        unit=own_unit,
        label="Trong căn A-1001",
    )
    foreign = Location(
        building=building,
        floor=floor,
        location_type=private_type,
        unit=other_unit,
        label="Trong căn A-1002",
    )
    db_session.add_all([building, floor, own_unit, other_unit, common_type, private_type, common, own, foreign])
    db_session.commit()

    rows = CatalogRepository(db_session).list_locations(
        building_id=building.id,
        resident_unit_id=own_unit.id,
    )

    assert {row.id for row in rows} == {common.id, own.id}
    assert foreign.id not in {row.id for row in rows}
