"""
Pydantic schemas for truck offloading workflows.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.truck_offloading import TruckOffloadingStatus, TruckOffloadingStep


class TruckOffloadingCreate(BaseModel):
    truck_registration: str = Field(..., max_length=30)
    driver_name: str = Field(..., max_length=120)
    driver_license: Optional[str] = Field(None, max_length=60)
    transporter_name: str = Field(..., max_length=120)
    client: str = Field(..., max_length=120)
    delivery_note_number: str = Field(..., max_length=80)
    commodity_type: str = Field(..., max_length=120)
    quantity: float = Field(..., ge=0)
    unit: str = Field(..., max_length=30)
    horse_registration: Optional[str] = Field(None, max_length=30)
    notes: Optional[str] = None


class TruckOffloadingDamageReport(BaseModel):
    damage_type: str = Field(..., max_length=60)
    severity: str = Field(..., max_length=40)
    location: str = Field(..., max_length=120)
    description: str = Field(..., max_length=1000)


class TruckOffloadingDamageAssessmentComplete(BaseModel):
    driver_name: str = Field(..., max_length=120)
    driver_comments: Optional[str] = Field(None, max_length=1000)


class TruckOffloadingSignoff(BaseModel):
    driver_name: str = Field(..., max_length=120)
    actual_quantity: Optional[float] = Field(None, ge=0)
    variance_notes: Optional[str] = Field(None, max_length=1000)


class TruckOffloadingResponse(BaseModel):
    id: UUID
    truck_registration: str
    driver_name: str
    driver_license: Optional[str]
    transporter_name: str
    client: str
    delivery_note_number: str
    commodity_type: str
    quantity: float
    unit: str
    horse_registration: Optional[str]
    notes: Optional[str]

    status: TruckOffloadingStatus
    current_step: TruckOffloadingStep
    arrival_photos: int
    offloading_photos: int
    damage_photos: int
    completion_photos: int
    damage_reported: bool
    damage_type: Optional[str]
    damage_severity: Optional[str]
    damage_location: Optional[str]
    damage_description: Optional[str]
    damage_signoff_name: Optional[str]
    damage_signoff_comments: Optional[str]
    damage_signoff_at: Optional[datetime]
    damage_assessment_completed: bool
    signoff_name: Optional[str]
    signoff_at: Optional[datetime]
    actual_quantity: Optional[float]
    variance_notes: Optional[str]

    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
    model_config = ConfigDict(from_attributes=True)
