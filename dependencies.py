from typing import List
from fastapi import Depends, HTTPException, status
from models.user import User
from core.security import get_current_user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        # user.role is a string, not an Enum
        user_role = str(user.role)
        
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required roles: {self.allowed_roles}"
            )
        return user

# Define reusable dependencies
require_admin = RoleChecker(["ADMIN", "SUPERUSER"])
require_supervisor = RoleChecker(["SUPERVISOR"])
require_management = RoleChecker(["ADMIN", "SUPERVISOR", "SUPERUSER"])