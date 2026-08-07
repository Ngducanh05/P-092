from src.models.enums import Category, ClassificationStatus, Priority, Severity, TicketStatus, UserRole


def test_self_dev_v2_roles_are_exactly_two():
    assert [x.value for x in UserRole] == ["RESIDENT", "COORDINATOR"]


def test_p0_is_not_a_priority():
    assert [x.value for x in Priority] == ["P1", "P2", "P3"]
    assert ClassificationStatus.MANUAL_REVIEW.value == "MANUAL_REVIEW"


def test_business_lifecycle_is_self_dev_v2():
    assert {x.value for x in TicketStatus} == {
        "NEW", "WAITING_RESIDENT_INFO", "APPROVED", "IN_PROGRESS",
        "COMPLETED", "UNRESOLVABLE", "CANCELLED",
    }


def test_canonical_category_and_severity_taxonomy():
    assert {x.value for x in Category} == {
        "WATER_LEAK", "ELECTRICAL_SHORT", "ELEVATOR", "SERIOUS_SECURITY_DISORDER",
        "LOCK_DOOR", "HVAC", "LOCAL_POWER_OUTAGE", "STRUCTURAL_ISSUE",
        "COMMON_LIGHT", "ODOR_HYGIENE", "NOISE_NEIGHBOR",
    }
    assert [x.value for x in Severity] == ["LOW", "MEDIUM", "HIGH"]
