# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from core.database import get_db
from services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """Dependency to get current authenticated user."""
    # Try to get token from Authorization header first
    if token:
        return AuthService.get_user_from_token(token, db)
    
    # Try to get token from cookies if header not present
    token_from_cookie = request.cookies.get("access_token")
    if token_from_cookie:
        return AuthService.get_user_from_token(token_from_cookie, db)
    
    # No token found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )