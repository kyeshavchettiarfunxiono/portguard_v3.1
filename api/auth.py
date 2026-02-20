# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from services.auth_service import AuthService
from schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user account."""
    requested_role = str(user_in.role).strip().upper()
    if requested_role in {"ADMIN", "SUPERUSER"}:
        raise HTTPException(
            status_code=403,
            detail="Privileged roles cannot be self-registered. Contact an administrator."
        )
    user_in.role = requested_role
    return AuthService.register_user(user_in, db)


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return access token."""
    user = AuthService.authenticate_user(form_data.username, form_data.password, db)
    access_token = AuthService.create_access_token(
        data={"sub": user.email, "role": user.role}
    )
    
    # Create response with token and role
    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "user": user.email
    })
    
    # Set token as cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=7*24*60*60,  # 7 days
        httponly=True,  # True to prevent XSS attacks (JS cannot read this cookie)
        samesite="lax",
        secure=False  # Set to True if running over HTTPS in production
    )
    
    return response


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return current_user
