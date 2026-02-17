# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 
# Docker Configured & new project directory has been created for this version on github at the following link: 

from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid
from core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    username = Column(String, unique=True, index=True, nullable=False)  # type: ignore
    email = Column(String, unique=True, index=True, nullable=False)  # type: ignore
    is_active = Column(Boolean, default=True)  # type: ignore
    hashed_password = Column(String, nullable=False)  # type: ignore
    role = Column(String, default="OPERATOR")  # type: ignore  # OPERATOR, SUPERVISOR, or SUPERUSER