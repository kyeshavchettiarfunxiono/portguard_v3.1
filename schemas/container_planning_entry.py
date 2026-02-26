from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContainerPlanningCreateRequest(BaseModel):
    planning_date: date
    booking_id: UUID | None = None
    booking_reference: str | None = Field(default=None, max_length=120)
    vessel_name: str = Field(..., min_length=1, max_length=160)
    client_name: str = Field(..., min_length=1, max_length=120)
    container_type: str = Field(..., min_length=1, max_length=40)
    planned_quantity: int = Field(..., ge=1)
    notes: str | None = Field(default=None, max_length=5000)


class ContainerPlanningResponse(BaseModel):
    id: UUID
    planning_date: date
    booking_id: UUID | None
    booking_reference: str | None
    vessel_name: str
    client_name: str
    container_type: str
    planned_quantity: int
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContainerPlanningSummaryResponse(BaseModel):
    planning_date: date
    planned_containers: int
    actual_containers: int
    variance: int
    completed_containers: int


class BookingOptionResponse(BaseModel):
    id: UUID
    booking_reference: str
    vessel_name: str
    client: str
    container_type: str
