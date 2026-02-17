from typing import List
from fastapi import Depends, HTTPException, status
from models.user import User
from core.security import get_current_user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        # Handle both Enum and String roles safely
        user_role = str(user.role.value) if hasattr(user.role, 'value') else str(user.role)
        
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {self.allowed_roles}"
            )
        return user

# Define reusable dependencies
require_admin = RoleChecker(["ADMIN"])
require_supervisor = RoleChecker(["SUPERVISOR", "ADMIN"])
require_management = RoleChecker(["ADMIN", "SUPERVISOR", "MANAGEMENT", "MANAGER"])
