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
    exterior_required: int = 3
    door_required: int = 2
    interior_required: int = 3
    cargo_required: int = 2
    
    # Damage tracking
    damage_reported: bool
    damage_description: Optional[str]
    
    # Cargo
    cargo_items_count: int
    model_config = ConfigDict(from_attributes=True)
