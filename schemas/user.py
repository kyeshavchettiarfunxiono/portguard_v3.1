# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 
# Docker Configured & new project directory has been created for this version on github at the following link: 


from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from uuid import UUID

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)
    role: str = "OPERATOR" # Default role

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)