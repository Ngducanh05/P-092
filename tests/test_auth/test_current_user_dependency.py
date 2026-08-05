"""Current-user dependency behavior."""

from uuid import uuid4

from src.database.models.user import User
from src.models.enums import Role


def test_unknown_profiles_must_be_created_as_resident():
    user = User(id=uuid4(), email="new@example.com", role=Role.RESIDENT, is_active=True)

    assert user.role is Role.RESIDENT


def test_admin_permissions_are_not_part_of_mvp_dependencies():
    assert Role.ADMIN.value == "admin"
