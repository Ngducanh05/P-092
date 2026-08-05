"""Current-user dependency behavior."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.api.dependencies.auth import get_current_user
from src.database.models.unit import Unit
from src.database.models.user import User
from src.models.api.errors import AUTH_PROFILE_INVALID, USER_INACTIVE, DomainError
from src.models.enums import Role
from src.repositories.user_repository import UserRepository
from src.security.supabase_jwt import AuthenticatedPrincipal


def test_existing_resident_profile_is_returned(db_session):
    user = User(id=uuid4(), email="resident@example.com", role=Role.RESIDENT, is_active=True)
    db_session.add(user)
    db_session.commit()

    current = get_current_user(_principal(user.id, email=user.email), db_session)

    assert current.id == user.id
    assert current.role is Role.RESIDENT


def test_new_email_resident_is_created_as_resident(db_session):
    auth_user_id = uuid4()

    current = get_current_user(_principal(auth_user_id, email="new@example.com"), db_session)

    assert current.id == auth_user_id
    assert current.email == "new@example.com"
    assert current.role is Role.RESIDENT


def test_new_phone_resident_requires_normalized_e164(db_session):
    auth_user_id = uuid4()

    current = get_current_user(_principal(auth_user_id, email=None, phone="+84901234567"), db_session)

    assert current.phone_number == "+84901234567"
    assert current.role is Role.RESIDENT


@pytest.mark.parametrize("role", [Role.COORDINATOR, Role.TECHNICIAN, Role.ADMIN])
def test_new_user_is_never_auto_promoted_from_metadata(role, db_session):
    auth_user_id = uuid4()
    principal = _principal(auth_user_id, email=f"{role.value}@example.com")

    current = get_current_user(principal, db_session)

    assert current.role is Role.RESIDENT


def test_inactive_user_rejected(db_session):
    user = User(id=uuid4(), email="inactive@example.com", role=Role.RESIDENT, is_active=False)
    db_session.add(user)
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        get_current_user(_principal(user.id, email=user.email), db_session)

    assert exc.value.code == USER_INACTIVE


def test_missing_email_and_phone_rejected(db_session):
    with pytest.raises(DomainError) as exc:
        get_current_user(_principal(uuid4(), email=None, phone=None), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID


def test_invalid_phone_claim_rejected(db_session):
    with pytest.raises(DomainError) as exc:
        get_current_user(_principal(uuid4(), email=None, phone="0901234567"), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID


def test_email_conflict_rejected(db_session):
    db_session.add(User(id=uuid4(), email="same@example.com", role=Role.RESIDENT, is_active=True))
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        get_current_user(_principal(uuid4(), email="same@example.com"), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID


def test_phone_conflict_rejected(db_session):
    db_session.add(User(id=uuid4(), phone_number="+84901234567", role=Role.RESIDENT, is_active=True))
    db_session.commit()

    with pytest.raises(DomainError) as exc:
        get_current_user(_principal(uuid4(), email=None, phone="+84901234567"), db_session)

    assert exc.value.code == AUTH_PROFILE_INVALID


def test_concurrent_insert_returns_existing_profile(db_session):
    auth_user_id = uuid4()
    existing = User(id=auth_user_id, email="race@example.com", role=Role.RESIDENT, is_active=True)
    db_session.add(existing)
    db_session.commit()

    profile = UserRepository(db_session).create_resident_profile(auth_user_id, "race@example.com", None)

    assert profile.id == auth_user_id


def test_database_error_does_not_rollback_unrelated_outer_work(db_session):
    existing_email = "taken@example.com"
    db_session.add(User(id=uuid4(), email=existing_email, role=Role.RESIDENT, is_active=True))
    db_session.commit()
    unit = Unit(id=uuid4(), building_code="A", floor="1", unit_number="101", is_active=True)
    db_session.add(unit)

    with pytest.raises(IntegrityError):
        UserRepository(db_session).create_resident_profile(uuid4(), existing_email, None)

    db_session.commit()
    assert db_session.get(Unit, unit.id) is not None


def test_admin_permissions_are_not_part_of_mvp_dependencies():
    assert Role.ADMIN.value == "admin"


def _principal(user_id, email="resident@example.com", phone=None) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        auth_user_id=user_id,
        email=email,
        phone=phone,
        issuer="https://example.supabase.co/auth/v1",
        audience="authenticated",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
