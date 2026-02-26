from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContainerPlanUpsertRequest(BaseModel):
    stack_priority: int = Field(default=3, ge=1, le=5)
    yard_zone: str | None = Field(default=None, max_length=120)
    planned_date: datetime | None = None
    plan_notes: str | None = Field(default=None, max_length=5000)


class ContainerPlanResponse(BaseModel):
    id: UUID
    container_id: UUID
    stack_priority: int
    yard_zone: str | None
    planned_date: datetime | None
    plan_notes: str | None
    created_at: datetime
    updated_at: datetime
    created_by: UUID | None
    modified_by: UUID | None

    model_config = ConfigDict(from_attributes=True)


class ContainerPlanningBoardItem(BaseModel):
    container_id: UUID
    container_no: str
    type: str
    status: str
    client: str | None
    vessel_name: str | None
    notes: str | None
    modified_at: datetime | None
    stack_priority: int | None = None
    yard_zone: str | None = None
    planned_date: datetime | None = None
    plan_notes: str | None = None
    plan_updated_at: datetime | None = None
    has_plan: bool = False
