"""
Pydantic schemas for packing workflow management.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from models.packing import PackingStep


class PackingSessionBase(BaseModel):
    """Base packing session schema."""
    model_config = ConfigDict(from_attributes=True)


class PackingSessionResponse(PackingSessionBase):
    """Response schema for packing session with progress tracking."""
    id: UUID
    container_id: UUID
    current_step: PackingStep
    
    # Photo counts
    before_packing_photos: int = 0
    cargo_photos: int = 0
    after_packing_photos: int = 0
    seal_photo_count: int = 0
    
    # Sealing info
    seal_number: Optional[str] = None
    gross_mass: Optional[str] = None
    tare_weight: Optional[str] = None
    
    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime


class PackingStepRequest(BaseModel):
    """Request to advance to next step."""
    container_id: UUID = Field(..., description="Container ID to advance")


class SealingRequest(BaseModel):
    """Request to complete sealing step."""
    container_id: UUID
    seal_number: str = Field(..., min_length=1, max_length=100)
    gross_mass: Optional[str] = None
    tare_weight: Optional[str] = None


class PhotoUploadRequest(BaseModel):
    """Request for photo upload tracking."""
    container_id: UUID
    step: PackingStep
    photo_count: int = Field(1, ge=1)
