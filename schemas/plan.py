from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class PlanCreate(BaseModel):
    booking_id: UUID
    planned_quantity: int = Field(..., ge=1)
    planned_date: datetime


class PlanUpdate(BaseModel):
    planned_quantity: Optional[int] = Field(default=None, ge=1)
    planned_date: Optional[datetime] = None
    status: Optional[str] = None


class PlanResponse(BaseModel):
    id: UUID
    booking_id: UUID
    vessel_name: str
    planned_quantity: int
    planned_date: datetime
    status: str
    created_at: datetime
    created_by: Optional[UUID] = None
    model_config = ConfigDict(from_attributes=True)