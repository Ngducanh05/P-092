import pytest

from src.models import Category, Priority, Role, Severity, TicketStatus


@pytest.mark.parametrize(
    ("enum_class", "expected_values"),
    [
        (
            Role,
            [
                "resident",
                "coordinator",
                "technician",
                "admin",
            ],
        ),
        (
            TicketStatus,
            [
                "new",
                "analyzing",
                "waiting_assignment",
                "assigned",
                "in_progress",
                "resolved",
                "closed",
                "rejected",
            ],
        ),
        (
            Category,
            [
                "electricity",
                "water",
                "elevator",
                "security",
                "sanitation",
                "fire_safety",
                "infrastructure",
                "other",
            ],
        ),
        (
            Severity,
            [
                "low",
                "medium",
                "high",
                "critical",
            ],
        ),
        (
            Priority,
            [
                "p1",
                "p2",
                "p3",
                "p4",
            ],
        ),
    ],
)
def test_enum_values_are_stable(enum_class, expected_values):
    assert [member.value for member in enum_class] == expected_values


@pytest.mark.parametrize(
    "enum_member",
    [
        Role.RESIDENT,
        TicketStatus.NEW,
        Category.WATER,
        Severity.HIGH,
        Priority.P2,
    ],
)
def test_enum_members_behave_as_strings(enum_member):
    assert isinstance(enum_member, str)
    assert enum_member == enum_member.value


@pytest.mark.parametrize(
    ("enum_class", "raw_value", "expected_member"),
    [
        (Role, "resident", Role.RESIDENT),
        (TicketStatus, "waiting_assignment", TicketStatus.WAITING_ASSIGNMENT),
        (Category, "fire_safety", Category.FIRE_SAFETY),
        (Severity, "critical", Severity.CRITICAL),
        (Priority, "p1", Priority.P1),
    ],
)
def test_valid_raw_strings_construct_enum_members(enum_class, raw_value, expected_member):
    assert enum_class(raw_value) is expected_member


@pytest.mark.parametrize(
    "enum_class",
    [
        Role,
        TicketStatus,
        Category,
        Severity,
        Priority,
    ],
)
def test_invalid_raw_strings_raise_value_error(enum_class):
    with pytest.raises(ValueError):
        enum_class("invalid")
