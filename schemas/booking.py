from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime


class BookingCreate(BaseModel):
    booking_reference: str
    booking_type: str = "EXPORT"
    client: str
    vessel_name: str
    voyage_number: str | None = None
    arrival_voyage: str | None = None
    date_in_depot: datetime | None = None
    container_type: str
    category: str | None = None
    notes: str | None = None


class BookingResponse(BaseModel):
    id: UUID
    booking_reference: str
    booking_type: str
    client: str
    vessel_name: str
    voyage_number: str | None
    arrival_voyage: str | None
    date_in_depot: datetime | None
    container_type: str
    category: str | None
    notes: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
