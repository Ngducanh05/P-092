"""Actor authorization exports for the Self Dev v2 two-role model."""

from src.api.dependencies.auth import require_coordinator, require_resident

__all__ = ["require_coordinator", "require_resident"]
