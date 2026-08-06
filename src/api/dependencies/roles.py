"""Compatibility exports for actor authorization dependencies."""

from src.api.dependencies.auth import require_bql, require_resident

__all__ = ["require_bql", "require_resident"]
