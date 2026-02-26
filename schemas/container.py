"""
Pydantic schemas for Container models with validation.
Integrates with models.container for single source of truth on Enums.
"""
import re
from datetime import datetime

# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 
# Docker Configured & new project directory has been created for this version on github at the following link: 


from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, ConfigDict
# Import the actual Enums from your model to ensure perfect alignment
from models.container import ContainerType, ContainerStatus

class ContainerBase(BaseModel):
    """Base fields shared across create, update, and response schemas."""
    container_no: str = Field(
        ...,
        min_length=11,
        max_length=11,
        description="Container number in ISO 6346 format (4 letters + 7 digits, e.g., MSMU4557285)"
    )
    booking_id: UUID = Field(..., description="UUID of the associated booking")
    type: ContainerType = Field(..., description="Container type (20FT, 40FT, or HC)")
    
    # Standard Pydantic V2 Configuration
    model_config = ConfigDict(from_attributes=True)

    @field_validator("container_no", mode="before")
    @classmethod
    def validate_container_no(cls, v: str) -> str:
        """Enforces the 4-letter + 7-number format for terminal operations."""
        if not isinstance(v, str):
            raise ValueError("Container number must be a string")
        
        v = v.upper().strip()
        pattern = r"^[A-Z]{4}[0-9]{7}$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid format: '{v}'. Expected 4 uppercase letters + 7 digits (e.g., MSMU4557285)."
            )
        return v

class ContainerCreate(ContainerBase):
    """Schema for registering a new container."""
    seal_no: Optional[str] = Field(None, max_length=50)
    gross_mass: Optional[float] = Field(None, ge=0)
    client: Optional[str] = Field(None, description="Client name (e.g., HULAMIN, PG_BISON)")
    client_reference: Optional[dict] = Field(None, description="Client-specific reference (e.g., RE numbers for Hulamin, HEXP for PG Bison)")
    notes: Optional[str] = Field(None, description="Additional notes or special instructions")
    
    # FCL Import-Specific Fields
    cargo_type: Optional[str] = Field(None, description="Type of cargo (e.g., Groupage Cargo, Steel, Automotive)")
    arrival_date: Optional[datetime] = Field(None, description="Date when container arrived at port")
    unpacking_location: Optional[str] = Field(None, description="Location where container will be unpacked")
    manifest_vessel_name: Optional[str] = Field(None, description="Manual vessel name captured from import manifest")
    manifest_voyage_number: Optional[str] = Field(None, description="Manual voyage number captured from import manifest")
    depot_list_fcl_count: Optional[int] = Field(None, ge=0, description="FCL count from depot list")
    depot_list_grp_count: Optional[int] = Field(None, ge=0, description="Groupage count from depot list")
    # The default status is handled by the DB Model as 'REGISTERED'

class ContainerUpdate(BaseModel):
    """Schema for updating container properties or status transitions."""
    status: Optional[ContainerStatus] = None
    seal_no: Optional[str] = None
    gross_mass: Optional[float] = None
    tare_weight: Optional[float] = None
    created_by: Optional[str] = None

    
    @field_validator("gross_mass", "tare_weight")
    @classmethod
    def validate_positive_mass(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Mass values must be non-negative")
        return v

class ContainerResponse(ContainerBase):
    """Full representation of a container for API responses."""
    id: UUID
    status: ContainerStatus
    seal_no: Optional[str] = None
    gross_mass: Optional[float] = None
    tare_weight: Optional[float] = None
    client: Optional[str] = None
    client_reference: Optional[dict] = None
    notes: Optional[str] = None
    vessel_name: Optional[str] = None  # Populated from booking
    
    # FCL Import-Specific Fields
    cargo_type: Optional[str] = None
    arrival_date: Optional[datetime] = None
    unpacking_location: Optional[str] = None
    manifest_vessel_name: Optional[str] = None
    manifest_voyage_number: Optional[str] = None
    depot_list_fcl_count: Optional[int] = None
    depot_list_grp_count: Optional[int] = None
    
    # Audit trail fields for the 8 Supervisors
    created_at: datetime
    created_by: Optional[UUID] = None
    modified_by: Optional[UUID] = None
    finalized_by_email: Optional[str] = None 
    modified_at: Optional[datetime] = None

class ContainerListResponse(BaseModel):
    """Paginated response for the Supervisor Review Queue."""
    items: List[ContainerResponse]
    total: int
    page: int
    page_size: int