from enum import Enum


class TicketStatus(str, Enum):  # noqa: UP042
    """Lifecycle states for a maintenance ticket."""

    NEW = "new"
    ANALYZING = "analyzing"
    WAITING_ASSIGNMENT = "waiting_assignment"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


class Category(str, Enum):  # noqa: UP042
    """Issue categories recognized by the FixIt agent."""

    ELECTRICITY = "electricity"
    WATER = "water"
    ELEVATOR = "elevator"
    SECURITY = "security"
    SANITATION = "sanitation"
    FIRE_SAFETY = "fire_safety"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"


class Severity(str, Enum):  # noqa: UP042
    """Severity levels assigned during ticket analysis."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(str, Enum):  # noqa: UP042
    """Priority labels produced by ticket scoring."""

    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class AssignmentStatus(str, Enum):  # noqa: UP042
    """Technician work states for a single ticket assignment."""

    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    UNABLE_TO_HANDLE = "unable_to_handle"
