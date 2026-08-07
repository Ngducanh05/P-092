from uuid import uuid4

from sqlalchemy import select

from src.database.models.audit_log import AuditLog
from src.database.models.building import Building
from src.database.models.category import CategoryCatalog
from src.database.models.floor import Floor
from src.database.models.location import Location
from src.database.models.location_type import LocationType
from src.database.models.notification import Notification
from src.database.models.resident_profile import ResidentProfile
from src.database.models.ticket import Ticket
from src.database.models.unit import Unit
from src.database.models.user_profile import UserProfile
from src.models.api.tickets import TicketCreateRequest
from src.models.enums import Category, ClassificationStatus, Priority, Severity, TicketStatus, UserRole
from src.request_context import request_id_context
from src.services.coordinator_service import CoordinatorService
from src.services.ticket_service import TicketService


def _seed_core(db_session):
    building = Building(code="A", name="Tòa A")
    floor = Floor(building=building, floor_code="10", display_name="Tầng 10", adjacency_index=10)
    unit = Unit(building=building, floor=floor, unit_code="A-1002")
    location_type = LocationType(code="CORRIDOR", display_name="Hành lang")
    location = Location(
        building=building,
        floor=floor,
        location_type=location_type,
        label="Hành lang tầng 10",
    )
    category = CategoryCatalog(code=Category.WATER_LEAK, display_name="Rò rỉ nước")

    resident_id = uuid4()
    second_resident_id = uuid4()
    coordinator_id = uuid4()
    resident = UserProfile(user_id=resident_id, phone_e164="+84901234567", role=UserRole.RESIDENT)
    second_resident = UserProfile(
        user_id=second_resident_id,
        phone_e164="+84907654321",
        role=UserRole.RESIDENT,
    )
    coordinator = UserProfile(user_id=coordinator_id, role=UserRole.COORDINATOR)
    resident_binding = ResidentProfile(user=resident, unit=unit, is_primary=True)
    second_binding = ResidentProfile(user=second_resident, unit=unit, is_primary=False)

    db_session.add_all(
        [
            building,
            floor,
            unit,
            location_type,
            location,
            category,
            resident,
            second_resident,
            coordinator,
            resident_binding,
            second_binding,
        ]
    )
    db_session.commit()
    return resident, second_resident, coordinator, resident_binding, location, category


def test_resident_create_then_coordinator_processes_directly_without_assignment(db_session):
    resident, second_resident, coordinator, binding, location, category = _seed_core(db_session)

    ticket = TicketService(db_session).create_ticket(
        resident.user_id,
        binding,
        TicketCreateRequest(location_id=location.id, description="Nước chảy ở hành lang"),
    )
    assert ticket.status == TicketStatus.NEW
    assert ticket.classification_status == ClassificationStatus.PROCESSING
    assert ticket.source_unit_id == binding.unit_id
    assert ticket.sla_started_at is not None

    # Simulate the backend-owned result after the AI boundary. No Technician/assignment is involved.
    locked = db_session.scalar(select(Ticket).where(Ticket.id == ticket.id))
    locked.classification_status = ClassificationStatus.RESOLVED
    locked.category_id = category.id
    locked.category = category
    locked.severity = Severity.MEDIUM
    locked.priority = Priority.P1
    db_session.commit()

    request_id = str(uuid4())
    token = request_id_context.set(request_id)
    try:
        service = CoordinatorService(db_session)
        approved = service.approve(coordinator.user_id, ticket.id)
        assert approved.status == TicketStatus.APPROVED
        started = service.start(coordinator.user_id, ticket.id)
        assert started.status == TicketStatus.IN_PROGRESS
        completed = service.complete(coordinator.user_id, ticket.id)
        assert completed.status == TicketStatus.COMPLETED
    finally:
        request_id_context.reset(token)

    # Every resident account bound to the same unit receives workflow notifications.
    recipient_ids = set(db_session.scalars(select(Notification.recipient_user_id)))
    assert resident.user_id in recipient_ids
    assert second_resident.user_id in recipient_ids

    audits = list(db_session.scalars(select(AuditLog).order_by(AuditLog.id)))
    assert [row.action for row in audits] == ["APPROVE_TICKET", "START_TICKET", "COMPLETE_TICKET"]
    assert all(row.request_id is not None for row in audits)
    assert all(isinstance(row.id, int) and row.id > 0 for row in audits)


def test_two_resident_accounts_can_share_one_unit(db_session):
    resident, second_resident, _coordinator, binding, _location, _category = _seed_core(db_session)
    rows = list(db_session.scalars(select(ResidentProfile).where(ResidentProfile.unit_id == binding.unit_id)))
    assert {row.user_id for row in rows} == {resident.user_id, second_resident.user_id}
    assert sum(1 for row in rows if row.is_primary) == 1


def test_manual_review_source_must_match_latest_ai_prediction(db_session):
    from src.database.models.ai_analysis import AIAnalysisRun
    from src.models.api.coordinator import ManualReviewResolveRequest
    from src.models.api.errors import CATEGORY_REQUIRED, DomainError
    from src.models.enums import AnalysisRunStatus, ResolutionSource, SeveritySource

    resident, _second, coordinator, binding, location, water = _seed_core(db_session)
    electrical = CategoryCatalog(code=Category.ELECTRICAL_SHORT, display_name="Chập điện")
    db_session.add(electrical)
    db_session.flush()

    ticket = TicketService(db_session).create_ticket(
        resident.user_id,
        binding,
        TicketCreateRequest(location_id=location.id, description="Có nước và dây điện bất thường"),
    )
    ticket.classification_status = ClassificationStatus.MANUAL_REVIEW
    ticket.severity = Severity.HIGH
    db_session.add(
        AIAnalysisRun(
            ticket_id=ticket.id,
            run_number=1,
            text_model_version="text-v1",
            vision_model_version="vision-v1",
            text_categories=[Category.WATER_LEAK.value],
            image_categories=[Category.ELECTRICAL_SHORT.value],
            red_flag_text=False,
            red_flag_signal=False,
            severity=Severity.HIGH,
            severity_source=SeveritySource.VISION,
            category_match=False,
            status=AnalysisRunStatus.SUCCEEDED,
        )
    )
    db_session.commit()

    service = CoordinatorService(db_session)
    try:
        service.resolve_manual_review(
            coordinator.user_id,
            ticket.id,
            ManualReviewResolveRequest(
                category_id=water.id,
                resolution_source=ResolutionSource.IMAGE,
                reason="Chọn theo ảnh",
            ),
        )
    except DomainError as exc:
        assert exc.code == CATEGORY_REQUIRED
    else:
        raise AssertionError("IMAGE resolution must use a Category predicted by the image")
