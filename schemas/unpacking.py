"""
Pydantic schemas for unpacking operations.
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from uuid import UUID


class UnpackingSessionResponse(BaseModel):
    """Response model for unpacking session."""
    id: UUID
    container_id: UUID
    current_step: str
    is_complete: bool
    exterior_inspection_photos: int
    door_opening_photos: int
    interior_inspection_photos: int
    cargo_unloading_photos: int
    damage_reported: bool
    damage_description: Optional[str]
    damage_photo_count: int
    cargo_items_count: int
    manifest_complete: bool
    manifest_document_reference: Optional[str]
    manifest_notes: Optional[str]
    manifest_documented_at: Optional[datetime]
    manifest_documented_by: Optional[UUID]
    cargo_unloading_started_at: Optional[datetime]
    cargo_unloading_completed_at: Optional[datetime]
    cargo_unloading_duration_minutes: Optional[int]
    final_notes: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class UnpackingProgressResponse(BaseModel):
    """Response model for unpacking progress tracking."""
    container_id: UUID
    container_no: str
    container_type: str
    current_step: str
    is_complete: bool
    
    # Photo counts
    exterior_inspection_photos: int
    door_opening_photos: int
    interior_inspection_photos: int
    cargo_unloading_photos: int
    
    # Requirements
    exterior_required: int = 1
    door_required: int = 1
    interior_required: int = 2
    cargo_required: int = 2
    manifest_required: int = 0
    cargo_unloading_started_at: Optional[datetime] = None
    cargo_unloading_completed_at: Optional[datetime] = None
    cargo_unloading_duration_minutes: Optional[int] = None
    
    # Damage tracking
    damage_reported: bool
    damage_description: Optional[str]
    
    # Cargo
    cargo_items_count: int
    manifest_complete: bool
    manifest_document_reference: Optional[str] = None
    manifest_notes: Optional[str] = None
    manifest_documented_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
