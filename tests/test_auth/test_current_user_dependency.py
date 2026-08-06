"""Current actor dependency behavior."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.api.dependencies.auth import get_current_actor
from src.database.models.bql_staff import BQLStaff
from src.database.models.resident import Resident
from src.database.models.unit import Unit
from src.models.api.errors import AUTH_PROFILE_CONFLICT, AUTH_PROFILE_INVALID, USER_INACTIVE, DomainError
from src.repositories.profile_repository import ProfileRepository
from src.security.supabase_jwt import AuthenticatedPrincipal


def test_existing_active_resident_profile_is_returned(db_session):
    resident = Resident(id=uuid4(), phone_number="+84901234567", is_active=True)
    db_session.add(resident)
    db_session.commit()

    current = get_current_actor(_principal(resident.id, email=None, phone=resident.phone_number), db_session)

    assert current.actor_type == "resident"
    assert current.profile.id == resident.id


def test_valid_phone_token_auto_creates_resident(db_session):
    auth_user_id = uuid4()

    current = get_current_actor(_principal(auth_user_id, email=None, phone="+84901234567"), db_session)

    assert current.actor_type == "resident"
    assert current.profile.id == auth_user_id
    assert current.profile.phone_number == "+84901234567"


def test_email_only_unknown_auth_user_is_rejected(db_session):
    with pytest.raises(DomainError) as exc:
        get_current_actor(_principal(uuid4(), email="new@example.com", phone=None), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID


def test_existing_active_bql_profile_is_returned(db_session):
    bql_staff = BQLStaff(id=uuid4(), email="bql@example.com", is_active=True)
    db_session.add(bql_staff)
    db_session.commit()

    current = get_current_actor(_principal(bql_staff.id, email=bql_staff.email, phone=None), db_session)

    assert current.actor_type == "bql"
    assert current.profile.id == bql_staff.id


def test_bql_is_never_auto_created(db_session):
    with pytest.raises(DomainError) as exc:
        get_current_actor(_principal(uuid4(), email="bql@example.com", phone=None), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID
    assert db_session.query(BQLStaff).count() == 0


def test_inactive_resident_rejected(db_session):
    resident = Resident(id=uuid4(), phone_number="+84901234567", is_active=False)
    db_session.add(resident)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        get_current_actor(_principal(resident.id, email=None, phone=resident.phone_number), db_session)

    assert exc.value.code == USER_INACTIVE


def test_inactive_bql_rejected(db_session):
    bql_staff = BQLStaff(id=uuid4(), email="inactive@example.com", is_active=False)
    db_session.add(bql_staff)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        get_current_actor(_principal(bql_staff.id, email=bql_staff.email, phone=None), db_session)

    assert exc.value.code == USER_INACTIVE


def test_invalid_phone_claim_rejected(db_session):
    with pytest.raises(DomainError) as exc:
        get_current_actor(_principal(uuid4(), email=None, phone="0901234567"), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID


def test_resident_phone_conflict_rejected(db_session):
    db_session.add(Resident(id=uuid4(), phone_number="+84901234567", is_active=True))
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        get_current_actor(_principal(uuid4(), email=None, phone="+84901234567"), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID


def test_bql_email_conflict_rejected(db_session):
    bql_staff = BQLStaff(id=uuid4(), email="same@example.com", is_active=True)
    db_session.add(bql_staff)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        get_current_actor(_principal(bql_staff.id, email="other@example.com", phone=None), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID


def test_same_auth_uuid_in_both_tables_is_rejected(db_session):
    auth_user_id = uuid4()
    db_session.add_all(
        [
            Resident(id=auth_user_id, phone_number="+84901234567", is_active=True),
            BQLStaff(id=auth_user_id, email="bql@example.com", is_active=True),
        ]
    )
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        get_current_actor(_principal(auth_user_id, email="bql@example.com", phone="+84901234567"), db_session)

    assert exc.value.code == AUTH_PROFILE_CONFLICT


def test_editable_metadata_cannot_promote_actor(db_session):
    current = get_current_actor(_principal(uuid4(), email="bql@example.com", phone="+84901234567"), db_session)

    assert current.actor_type == "resident"
    assert db_session.query(BQLStaff).count() == 0


def test_concurrent_insert_returns_existing_profile(db_session):
    auth_user_id = uuid4()
    existing = Resident(id=auth_user_id, phone_number="+84901234567", is_active=True)
    db_session.add(existing)
    db_session.commit()

    profile = ProfileRepository(db_session).create_resident_profile(auth_user_id, "+84901234567")

    assert profile.id == auth_user_id


def test_database_error_does_not_rollback_unrelated_outer_work(db_session):
    existing_phone = "+84901234567"
    db_session.add(Resident(id=uuid4(), phone_number=existing_phone, is_active=True))
    db_session.commit()
    unit = Unit(id=uuid4(), building_code="A", floor="1", unit_number="101", is_active=True)
    db_session.add(unit)

    with pytest.raises(IntegrityError):
        ProfileRepository(db_session).create_resident_profile(uuid4(), existing_phone)

    db_session.commit()
    assert db_session.get(Unit, unit.id) is not None


def _principal(user_id, email="resident@example.com", phone=None) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        auth_user_id=user_id,
        email=email,
        phone=phone,
        issuer="https://example.supabase.co/auth/v1",
        audience="authenticated",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
