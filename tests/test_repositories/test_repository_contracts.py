"""Repository contract tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from src.database.models.attachment import TicketAttachment
from src.database.models.resident import Resident
from src.database.models.resident_unit_membership import ResidentUnitMembership
from src.database.models.ticket import Ticket
from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
from src.database.models.unit import Unit
from src.models.enums import Category, Priority, TicketStatus
from src.repositories.ticket_repository import TicketRepository
from src.repositories.unit_repository import UnitRepository

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_ticket_repository_exposes_scoped_methods_only():
    text = (PROJECT_ROOT / "src" / "repositories" / "ticket_repository.py").read_text(encoding="utf-8")

    assert "list_resident_accessible_tickets" in text
    assert "get_resident_accessible_ticket" in text
    assert "list_bql_tickets" in text
    assert "get_ticket_by_id_for_bql" in text
    assert "def list_all" not in text
    assert "def get_any" not in text


def test_unit_repository_uses_active_membership_predicates():
    text = (PROJECT_ROOT / "src" / "repositories" / "unit_repository.py").read_text(encoding="utf-8")

    assert "ResidentUnitMembership.is_active.is_(True)" in text
    assert "Unit.is_active.is_(True)" in text


def test_active_membership_filtering_excludes_inactive_records(db_session):
    resident = _resident()
    active_unit = _unit("A")
    inactive_unit = _unit("B", is_active=False)
    inactive_membership_unit = _unit("C")
    db_session.add_all(
        [
            resident,
            active_unit,
            inactive_unit,
            inactive_membership_unit,
            _membership(resident.id, active_unit.id, True),
            _membership(resident.id, inactive_unit.id, True),
            _membership(resident.id, inactive_membership_unit.id, False),
        ]
    )
    db_session.commit()

    units = UnitRepository(db_session).list_active_memberships_for_resident(resident.id)

    assert [unit.id for unit in units] == [active_unit.id]


def test_resident_ticket_isolation_order_and_eager_attachments(db_session):
    resident = _resident()
    other = _resident()
    unit = _unit("A")
    other_unit = _unit("B")
    db_session.add_all([resident, other, unit, other_unit, _membership(resident.id, unit.id), _membership(other.id, other_unit.id)])
    old_ticket = _ticket(resident.id, unit.id, "Old", created_at=datetime.now(UTC) - timedelta(days=2))
    new_ticket = _ticket(resident.id, unit.id, "New", created_at=datetime.now(UTC) - timedelta(days=1))
    other_ticket = _ticket(other.id, other_unit.id, "Other")
    attachment = TicketAttachment(
        id=uuid4(),
        ticket=new_ticket,
        file_url="tickets/path.jpg",
        file_type="image",
        mime_type="image/jpeg",
        file_size=10,
    )
    db_session.add_all([old_ticket, new_ticket, other_ticket, attachment])
    db_session.commit()

    items, total = TicketRepository(db_session).list_resident_accessible_tickets(resident.id, 1, 10)

    assert total == 2
    assert [item.id for item in items] == [new_ticket.id, old_ticket.id]
    assert items[0].attachments[0].id == attachment.id


def test_bql_ordering_filters_and_pagination(db_session):
    resident, unit = _resident_with_unit(db_session)
    p2_old = _ticket(resident.id, unit.id, "P2 old", priority=Priority.P2, created_at=datetime.now(UTC) - timedelta(days=2))
    p1_new = _ticket(resident.id, unit.id, "P1 new", priority=Priority.P1, created_at=datetime.now(UTC) - timedelta(days=1))
    p2_new = _ticket(resident.id, unit.id, "P2 new", priority=Priority.P2, category=Category.WATER)
    null_priority = _ticket(resident.id, unit.id, "Null", priority=None)
    db_session.add_all([p2_old, p1_new, p2_new, null_priority])
    db_session.commit()

    items, total = TicketRepository(db_session).list_bql_tickets(1, 3)
    water_items, water_total = TicketRepository(db_session).list_bql_tickets(1, 10, category=Category.WATER)

    assert total == 4
    assert [item.id for item in items] == [p1_new.id, p2_old.id, p2_new.id]
    assert water_total == 1
    assert water_items[0].id == p2_new.id


def test_attachment_lookup_and_upload_session_lock_select(db_session):
    resident, unit = _resident_with_unit(db_session)
    ticket = _ticket(resident.id, unit.id, "Ticket")
    attachment = TicketAttachment(
        id=uuid4(),
        ticket=ticket,
        file_url="tickets/path.jpg",
        file_type="image",
        mime_type="image/jpeg",
        file_size=10,
    )
    upload_session = TicketAttachmentUploadSession(
        id=uuid4(),
        resident_id=resident.id,
        storage_path=f"tickets/{resident.id}/2026/08/{uuid4()}.jpg",
        original_filename="photo.jpg",
        mime_type="image/jpeg",
        file_size=10,
        status="pending",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add_all([ticket, attachment, upload_session])
    db_session.commit()
    repo = TicketRepository(db_session)

    assert repo.get_attachment_for_ticket(ticket.id, attachment.id).id == attachment.id
    assert repo.get_attachment_for_ticket(uuid4(), attachment.id) is None
    assert [session.id for session in repo.lock_upload_sessions([upload_session.id])] == [upload_session.id]


def _resident_with_unit(db_session):
    resident = _resident()
    unit = _unit("A")
    db_session.add_all([resident, unit, _membership(resident.id, unit.id)])
    db_session.commit()
    return resident, unit


def _resident() -> Resident:
    return Resident(id=uuid4(), phone_number=f"+8490{uuid4().int % 10_000_000:07d}", is_active=True)


def _unit(building_code: str, is_active: bool = True) -> Unit:
    return Unit(id=uuid4(), building_code=building_code, floor="10", unit_number="1001", is_active=is_active)


def _membership(resident_id, unit_id, is_active: bool = True) -> ResidentUnitMembership:
    return ResidentUnitMembership(id=uuid4(), resident_id=resident_id, unit_id=unit_id, is_active=is_active)


def _ticket(
    resident_id,
    unit_id,
    title: str,
    *,
    priority: Priority | None = Priority.P3,
    category: Category | None = Category.ELECTRICITY,
    created_at: datetime | None = None,
) -> Ticket:
    now = created_at or datetime.now(UTC)
    return Ticket(
        id=uuid4(),
        resident_id=resident_id,
        unit_id=unit_id,
        title=title,
        description=f"{title} description long enough",
        status=TicketStatus.NEW,
        category=category,
        priority=priority,
        created_at=now,
        updated_at=now,
    )
