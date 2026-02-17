from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class BookingCreate(BaseModel):
    booking_reference: str
    client: str
    vessel_name: str
    container_type: str


class BookingResponse(BaseModel):
    id: UUID
    booking_reference: str
    client: str
    vessel_name: str
    container_type: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
