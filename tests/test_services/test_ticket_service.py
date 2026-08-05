"""Ticket service behavior tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.database.models.attachment import TicketAttachment
from src.database.models.ticket import Ticket
from src.database.models.ticket_attachment_upload_session import TicketAttachmentUploadSession
from src.database.models.ticket_status_history import TicketStatusHistory
from src.database.models.unit import Unit
from src.database.models.user import User
from src.database.models.user_unit_membership import UserUnitMembership
from src.models.api.errors import (
    INVALID_ATTACHMENT,
    NO_ACTIVE_UNIT,
    STORAGE_NOT_CONFIGURED,
    UNIT_NOT_FOUND,
    UNIT_SELECTION_REQUIRED,
    DomainError,
)
from src.models.api.tickets import TicketCreateRequest
from src.models.enums import Role, TicketStatus
from src.services.storage_service import VerifiedStorageObject
from src.services.ticket_service import TicketService


def test_one_active_unit_is_automatically_selected(db_session):
    resident, unit = _resident_with_unit(db_session)
    service = TicketService(db_session, FakeStorage())

    ticket = service.create_ticket(resident, _request())

    assert ticket.unit_id == unit.id
    assert ticket.resident_id == resident.id
    assert ticket.status is TicketStatus.NEW
    assert db_session.query(TicketStatusHistory).count() == 1


def test_multiple_active_units_without_unit_id_requires_selection(db_session):
    resident, unit = _resident_with_unit(db_session)
    second = _unit("B")
    db_session.add_all([second, _membership(resident.id, second.id)])
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        TicketService(db_session, FakeStorage()).create_ticket(resident, _request())

    assert exc.value.code == UNIT_SELECTION_REQUIRED
    assert unit.id


def test_multiple_units_with_owned_unit_succeeds(db_session):
    resident, unit = _resident_with_unit(db_session)
    second = _unit("B")
    db_session.add_all([second, _membership(resident.id, second.id)])
    db_session.commit()

    ticket = TicketService(db_session, FakeStorage()).create_ticket(resident, _request(unit_id=second.id))

    assert ticket.unit_id == second.id


def test_submitted_unowned_unit_returns_not_found(db_session):
    resident, _unit_owned = _resident_with_unit(db_session)
    unowned = _unit("Z")
    db_session.add(unowned)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        TicketService(db_session, FakeStorage()).create_ticket(resident, _request(unit_id=unowned.id))

    assert exc.value.code == UNIT_NOT_FOUND


def test_no_active_unit_rejected(db_session):
    resident = _resident()
    db_session.add(resident)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        TicketService(db_session, FakeStorage()).create_ticket(resident, _request())

    assert exc.value.code == NO_ACTIVE_UNIT


def test_upload_session_is_locked_verified_persisted_and_consumed(db_session):
    resident, _unit = _resident_with_unit(db_session)
    upload_session = _upload_session(resident.id)
    db_session.add(upload_session)
    db_session.commit()

    ticket = TicketService(db_session, FakeStorage()).create_ticket(resident, _request(attachment_upload_ids=[upload_session.id]))
    attachment = db_session.query(TicketAttachment).filter_by(ticket_id=ticket.id).one()
    db_session.refresh(upload_session)

    assert attachment.file_url == upload_session.storage_path
    assert attachment.file_type == "image"
    assert attachment.mime_type == "image/jpeg"
    assert attachment.file_size == 10
    assert upload_session.status == "consumed"
    assert upload_session.consumed_at is not None
    assert upload_session.object_verified_at is not None


@pytest.mark.parametrize(
    "mutator",
    [
        lambda session, other_id: setattr(session, "owner_user_id", other_id),
        lambda session, _other_id: setattr(session, "status", "consumed"),
        lambda session, _other_id: setattr(session, "consumed_at", datetime.now(UTC)),
        lambda session, _other_id: setattr(session, "expires_at", datetime.now(UTC) - timedelta(minutes=1)),
    ],
)
def test_invalid_upload_sessions_rejected(mutator, db_session):
    resident, _unit = _resident_with_unit(db_session)
    upload_session = _upload_session(resident.id, created_at=datetime.now(UTC) - timedelta(hours=2))
    mutator(upload_session, uuid4())
    db_session.add(upload_session)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        TicketService(db_session, FakeStorage()).create_ticket(resident, _request(attachment_upload_ids=[upload_session.id]))

    assert exc.value.code == INVALID_ATTACHMENT
    assert db_session.query(Ticket).count() == 0


def test_missing_upload_session_rejected(db_session):
    resident, _unit = _resident_with_unit(db_session)

    with pytest.raises(DomainError) as exc:
        TicketService(db_session, FakeStorage()).create_ticket(resident, _request(attachment_upload_ids=[uuid4()]))

    assert exc.value.code == INVALID_ATTACHMENT


def test_storage_not_configured_with_attachment_rejected(db_session):
    resident, _unit = _resident_with_unit(db_session)
    upload_session = _upload_session(resident.id)
    db_session.add(upload_session)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        TicketService(db_session, FakeStorage(configured=False)).create_ticket(
            resident,
            _request(attachment_upload_ids=[upload_session.id]),
        )

    assert exc.value.code == STORAGE_NOT_CONFIGURED


def test_object_missing_rolls_back_and_does_not_consume_upload(db_session):
    resident, _unit = _resident_with_unit(db_session)
    upload_session = _upload_session(resident.id)
    db_session.add(upload_session)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        TicketService(db_session, FakeStorage(object_missing=True)).create_ticket(
            resident,
            _request(attachment_upload_ids=[upload_session.id]),
        )

    db_session.refresh(upload_session)
    assert exc.value.code == INVALID_ATTACHMENT
    assert upload_session.status == "pending"
    assert db_session.query(Ticket).count() == 0


def test_failure_before_commit_rolls_back_all_records(db_session):
    resident, _unit = _resident_with_unit(db_session)
    upload_session = _upload_session(resident.id)
    db_session.add(upload_session)
    db_session.commit()
    service = TicketService(db_session, FakeStorage())

    def raise_after_ticket(*args, **kwargs):
        raise RuntimeError("boom")

    service.tickets.create_attachments_from_upload_sessions = raise_after_ticket

    with pytest.raises(RuntimeError):
        service.create_ticket(resident, _request(attachment_upload_ids=[upload_session.id]))

    db_session.refresh(upload_session)
    assert db_session.query(Ticket).count() == 0
    assert db_session.query(TicketStatusHistory).count() == 0
    assert upload_session.status == "pending"


def test_duplicate_upload_ids_rejected_by_schema():
    upload_id = uuid4()

    with pytest.raises(ValueError):
        TicketCreateRequest(
            title="Broken pipe",
            description="A broken pipe is leaking in the hallway.",
            attachment_upload_ids=[upload_id, upload_id],
        )


def test_ticket_creation_does_not_create_ai_or_scoring_results(db_session):
    resident, _unit = _resident_with_unit(db_session)

    ticket = TicketService(db_session, FakeStorage()).create_ticket(resident, _request())

    assert ticket.category is None
    assert ticket.severity is None
    assert ticket.priority is None


class FakeStorage:
    settings = type("Settings", (), {"supabase_signed_download_ttl_seconds": 300})()

    def __init__(self, configured=True, object_missing=False):
        self.configured = configured
        self.object_missing = object_missing

    def is_owned_ticket_attachment_path(self, storage_path, user_id):
        return storage_path.startswith(f"tickets/{user_id}/")

    def verify_uploaded_object(self, storage_path, expected_mime_type=None, expected_file_size=None):
        if not self.configured:
            raise DomainError(STORAGE_NOT_CONFIGURED, "Supabase Storage is not configured.", 503)
        if self.object_missing:
            raise DomainError(INVALID_ATTACHMENT, "Uploaded attachment object was not found.", 400)
        return VerifiedStorageObject(
            mime_type=expected_mime_type or "image/jpeg",
            file_size=expected_file_size or 10,
            verified_at=datetime.now(UTC),
        )

    def create_signed_download_url(self, storage_path):
        return "https://storage.example/download"


def _request(**overrides) -> TicketCreateRequest:
    data = {
        "title": "Broken pipe",
        "description": "A broken pipe is leaking in the hallway.",
    }
    data.update(overrides)
    return TicketCreateRequest(**data)


def _resident_with_unit(db_session) -> tuple[User, Unit]:
    resident = _resident()
    unit = _unit("A")
    db_session.add_all([resident, unit, _membership(resident.id, unit.id)])
    db_session.commit()
    return resident, unit


def _resident() -> User:
    return User(id=uuid4(), email=f"{uuid4()}@example.com", role=Role.RESIDENT, is_active=True)


def _unit(building: str) -> Unit:
    return Unit(id=uuid4(), building_code=building, floor="10", unit_number="1001", is_active=True)


def _membership(user_id, unit_id) -> UserUnitMembership:
    return UserUnitMembership(id=uuid4(), user_id=user_id, unit_id=unit_id, is_active=True)


def _upload_session(user_id, created_at=None) -> TicketAttachmentUploadSession:
    created = created_at or datetime.now(UTC)
    return TicketAttachmentUploadSession(
        id=uuid4(),
        owner_user_id=user_id,
        storage_path=f"tickets/{user_id}/2026/08/{uuid4()}.jpg",
        original_filename="photo.jpg",
        mime_type="image/jpeg",
        file_size=10,
        status="pending",
        expires_at=created + timedelta(hours=1),
        created_at=created,
        updated_at=created,
    )
