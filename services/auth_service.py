# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv
import bcrypt

from models.user import User
from schemas.user import UserCreate

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_PORT_GUARD_KEY_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

# CryptContext with bcrypt configured to avoid 72-byte truncation
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Explicitly set rounds to 12 (recommended)
)


class AuthService:
    """Service layer for authentication and authorization."""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify plain password against hashed password."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a plain password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> dict:
        """Verify JWT token and return payload."""
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email_from_token = payload.get("sub")
            if email_from_token is None:
                raise credentials_exception
            return payload
        except JWTError:
            raise credentials_exception
    
    @staticmethod
    def register_user(user_in: UserCreate, db: Session) -> User:
        """Register a new user."""
        db_user = db.query(User).filter(  # type: ignore
            (User.email == user_in.email) | (User.username == user_in.username)
        ).first()
        
        if db_user:
            raise HTTPException(
                status_code=400,
                detail="User with this email or username already exists."
            )
        
        new_user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=AuthService.get_password_hash(user_in.password),
            role=user_in.role.upper()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    
    @staticmethod
    def authenticate_user(email: str, password: str, db: Session) -> User:
        """Authenticate user by email and password."""
        user = db.query(User).filter(User.email == email).first()  # type: ignore
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        
        user_password = str(user.hashed_password)
        if not AuthService.verify_password(password, user_password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        return user
    
    @staticmethod
    def get_user_from_token(token: str, db: Session) -> User:
        """Get user from JWT token."""
        payload = AuthService.verify_token(token)
        email_from_token = payload.get("sub")
        
        if email_from_token is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid token: no subject claim"
            )
        
        email: str = str(email_from_token)
        
        user = db.query(User).filter(User.email == email).first()  # type: ignore
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
