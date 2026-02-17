from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DamageReportPhotoResponse(BaseModel):
    id: UUID
    url: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DamageReportUpdateRequest(BaseModel):
    damage_type: str = Field(..., min_length=2, max_length=80)
    severity: str = Field(..., min_length=3, max_length=20)
    location: Optional[str] = Field(None, max_length=120)
    description: str = Field(..., min_length=3, max_length=5000)


class DamageReportResolveRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=5000)


class DamageReportResponse(BaseModel):
    id: UUID
    container_id: UUID
    container_no: str
    damage_type: str
    severity: str
    location: Optional[str] = None
    description: str
    photo_count: int
    needs_repair: bool
    is_resolved: bool
    resolved_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[UUID] = None
    reported_by: Optional[UUID] = None
    reported_at: datetime
    updated_at: datetime
    photos: list[DamageReportPhotoResponse] = []

    model_config = ConfigDict(from_attributes=True)
