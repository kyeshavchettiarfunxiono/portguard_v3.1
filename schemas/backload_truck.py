"""
Pydantic schemas for backload truck packing workflows.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from models.backload_truck import BackloadTruckStatus, BackloadTruckStep


class BackloadTruckCreate(BaseModel):
    truck_registration: str = Field(..., max_length=30)
    driver_name: str = Field(..., max_length=120)
    transporter_name: str = Field(..., max_length=120)
    client: str = Field(..., max_length=120)
    cargo_type: str = Field(..., max_length=120)
    cargo_description: str = Field(..., max_length=2000)
    delivery_destination: str = Field(..., max_length=200)
    quantity: float = Field(..., ge=0)
    unit: str = Field(..., max_length=30)

    horse_registration: Optional[str] = Field(None, max_length=30)
    driver_license: Optional[str] = Field(None, max_length=60)
    delivery_note_number: Optional[str] = Field(None, max_length=80)
    gross_weight: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = Field(None, max_length=2000)


class BackloadCargoItemCreate(BaseModel):
    description: str = Field(..., max_length=200)
    quantity: float = Field(..., ge=0)
    unit: str = Field(..., max_length=30)
    weight_kg: float = Field(..., ge=0)


class BackloadManifestUpdate(BaseModel):
    total_cargo_weight: float = Field(..., ge=0)
    transfer_order_number: Optional[str] = Field(None, max_length=80)


class BackloadTruckSignoff(BaseModel):
    driver_name: str = Field(..., max_length=120)


class BackloadCargoItemResponse(BaseModel):
    id: UUID
    description: str
    quantity: float
    unit: str
    weight_kg: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BackloadTruckResponse(BaseModel):
    id: UUID
    truck_registration: str
    driver_name: str
    transporter_name: str
    client: str
    cargo_type: str
    cargo_description: str
    delivery_destination: str
    quantity: float
    unit: str
    horse_registration: Optional[str]
    driver_license: Optional[str]
    delivery_note_number: Optional[str]
    gross_weight: Optional[float]
    notes: Optional[str]

    status: BackloadTruckStatus
    current_step: BackloadTruckStep
    before_photos: int
    packing_photos: int
    after_photos: int
    total_cargo_weight: Optional[float]
    transfer_order_number: Optional[str]
    model_config = ConfigDict(from_attributes=True)
    signoff_name: Optional[str]
    signoff_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    items: List[BackloadCargoItemResponse] = []
    model_config = ConfigDict(from_attributes=True)
