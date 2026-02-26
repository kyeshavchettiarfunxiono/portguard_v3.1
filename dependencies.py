"""Compatibility shim for legacy imports.

Use api.dependencies as the single source of truth for role guards.
"""

from api.dependencies import RoleChecker, require_admin, require_supervisor, require_management

__all__ = ["RoleChecker", "require_admin", "require_supervisor", "require_management"]