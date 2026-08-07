from enum import Enum


class UserRole(str, Enum):  # noqa: UP042
    """Application roles defined by Self_Dev_Docs v2."""

    RESIDENT = "RESIDENT"
    COORDINATOR = "COORDINATOR"


class TicketStatus(str, Enum):  # noqa: UP042
    """Business lifecycle states. P0 is deliberately not represented here."""

    NEW = "NEW"
    WAITING_RESIDENT_INFO = "WAITING_RESIDENT_INFO"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    UNRESOLVABLE = "UNRESOLVABLE"
    CANCELLED = "CANCELLED"


class ClassificationStatus(str, Enum):  # noqa: UP042
    """AI/classification state, independent from the business lifecycle."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RESOLVED = "RESOLVED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FAILED = "FAILED"


class Category(str, Enum):  # noqa: UP042
    """Canonical issue categories from Self_Dev_Docs v2."""

    WATER_LEAK = "WATER_LEAK"
    ELECTRICAL_SHORT = "ELECTRICAL_SHORT"
    ELEVATOR = "ELEVATOR"
    SERIOUS_SECURITY_DISORDER = "SERIOUS_SECURITY_DISORDER"
    LOCK_DOOR = "LOCK_DOOR"
    HVAC = "HVAC"
    LOCAL_POWER_OUTAGE = "LOCAL_POWER_OUTAGE"
    STRUCTURAL_ISSUE = "STRUCTURAL_ISSUE"
    COMMON_LIGHT = "COMMON_LIGHT"
    ODOR_HYGIENE = "ODOR_HYGIENE"
    NOISE_NEIGHBOR = "NOISE_NEIGHBOR"


class Severity(str, Enum):  # noqa: UP042
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Priority(str, Enum):  # noqa: UP042
    """Only real priorities. P0 is classification_status=MANUAL_REVIEW."""

    P1 = "P1"
    P2 = "P2"
    P3 = "P3"


class ResolutionSource(str, Enum):  # noqa: UP042
    IMAGE = "IMAGE"
    TEXT = "TEXT"
    OTHER = "OTHER"


class AttachmentType(str, Enum):  # noqa: UP042
    ISSUE_ORIGINAL = "ISSUE_ORIGINAL"
    RESIDENT_SUPPLEMENT = "RESIDENT_SUPPLEMENT"


class ImageQualityStatus(str, Enum):  # noqa: UP042
    PENDING = "PENDING"
    READABLE = "READABLE"
    UNREADABLE = "UNREADABLE"


class AnalysisRunStatus(str, Enum):  # noqa: UP042
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class SeveritySource(str, Enum):  # noqa: UP042
    VISION = "VISION"
    TEXT_FALLBACK = "TEXT_FALLBACK"


class InformationRequestStatus(str, Enum):  # noqa: UP042
    OPEN = "OPEN"
    RESPONDED = "RESPONDED"
    CLOSED = "CLOSED"


class NotificationChannel(str, Enum):  # noqa: UP042
    PUSH = "PUSH"
    SMS = "SMS"
    IN_APP = "IN_APP"


class NotificationStatus(str, Enum):  # noqa: UP042
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    READ = "READ"
