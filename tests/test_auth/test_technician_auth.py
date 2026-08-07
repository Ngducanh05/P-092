"""Technician actor resolution and auth-me endpoint tests."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.api.dependencies.auth import get_current_actor, require_technician
from src.database.models.bql_staff import BQLStaff
from src.database.models.resident import Resident
from src.database.models.technician_profile import TechnicianProfile
from src.models.api.errors import (
    ACTOR_FORBIDDEN,
    AUTH_PROFILE_CONFLICT,
    AUTH_PROFILE_INVALID,
    USER_INACTIVE,
    DomainError,
)
from src.security.supabase_jwt import AuthenticatedPrincipal


def _principal(user_id, email=None, phone=None) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        auth_user_id=user_id,
        email=email,
        phone=phone,
        issuer="https://example.supabase.co/auth/v1",
        audience="authenticated",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def _make_technician(db, **kwargs) -> TechnicianProfile:
    defaults = dict(
        id=uuid4(),
        email="tech@example.com",
        is_active=True,
        is_available=True,
    )
    defaults.update(kwargs)
    tech = TechnicianProfile(**defaults)
    db.add(tech)
    db.commit()
    return tech


class TestTechnicianActorResolution:
    def test_active_technician_is_resolved(self, db_session):
        tech = _make_technician(db_session)
        actor = get_current_actor(_principal(tech.id, email=tech.email), db_session)
        assert actor.actor_type == "technician"
        assert actor.profile.id == tech.id

    def test_technician_email_validated_case_insensitively(self, db_session):
        tech = _make_technician(db_session, email="Tech@Example.COM")
        actor = get_current_actor(_principal(tech.id, email="tech@example.com"), db_session)
        assert actor.actor_type == "technician"

    def test_inactive_technician_rejected_with_user_inactive(self, db_session):
        tech = _make_technician(db_session, is_active=False)
        with pytest.raises(DomainError) as exc:
            get_current_actor(_principal(tech.id, email=tech.email), db_session)
        assert exc.value.code == USER_INACTIVE

    def test_technician_email_mismatch_rejected(self, db_session):
        tech = _make_technician(db_session, email="real@example.com")
        with pytest.raises(DomainError) as exc:
            get_current_actor(_principal(tech.id, email="other@example.com"), db_session)
        assert exc.value.code == AUTH_PROFILE_INVALID

    def test_technician_email_missing_in_token_rejected(self, db_session):
        tech = _make_technician(db_session)
        with pytest.raises(DomainError) as exc:
            get_current_actor(_principal(tech.id, email=None, phone="+84901234567"), db_session)
        assert exc.value.code == AUTH_PROFILE_INVALID

    def test_technician_is_never_auto_provisioned_from_unknown_email(self, db_session):
        with pytest.raises(DomainError) as exc:
            get_current_actor(_principal(uuid4(), email="unknown@example.com"), db_session)
        assert exc.value.code == AUTH_PROFILE_INVALID
        assert db_session.query(TechnicianProfile).count() == 0

    def test_resident_and_technician_conflict_detected(self, db_session):
        uid = uuid4()
        db_session.add(Resident(id=uid, phone_number="+84901234567", is_active=True))
        db_session.add(TechnicianProfile(id=uid, email="tech@example.com", is_active=True))
        db_session.commit()
        with pytest.raises(DomainError) as exc:
            get_current_actor(_principal(uid, email="tech@example.com", phone="+84901234567"), db_session)
        assert exc.value.code == AUTH_PROFILE_CONFLICT

    def test_bql_and_technician_conflict_detected(self, db_session):
        uid = uuid4()
        db_session.add(BQLStaff(id=uid, email="bql@example.com", is_active=True))
        db_session.add(TechnicianProfile(id=uid, email="bql@example.com", is_active=True))
        db_session.commit()
        with pytest.raises(DomainError) as exc:
            get_current_actor(_principal(uid, email="bql@example.com"), db_session)
        assert exc.value.code == AUTH_PROFILE_CONFLICT

    def test_require_technician_raises_for_bql(self, db_session):
        bql = BQLStaff(id=uuid4(), email="bql@example.com", is_active=True)
        db_session.add(bql)
        db_session.commit()
        actor = get_current_actor(_principal(bql.id, email=bql.email), db_session)
        with pytest.raises(DomainError) as exc:
            require_technician(actor)
        assert exc.value.code == ACTOR_FORBIDDEN

    def test_require_technician_returns_profile_for_technician(self, db_session):
        tech = _make_technician(db_session)
        actor = get_current_actor(_principal(tech.id, email=tech.email), db_session)
        profile = require_technician(actor)
        assert profile.id == tech.id
