from datetime import datetime
from pydantic import BaseModel, ConfigDict
from uuid import UUID


class OperationalIncidentResponse(BaseModel):
    id: UUID
    title: str
    incident_type: str
    priority: str
    location: str | None
    reporter_name: str | None
    incident_at: datetime
    description: str
    created_at: datetime
    updated_at: datetime
    photos: list[dict]

    model_config = ConfigDict(from_attributes=True)
