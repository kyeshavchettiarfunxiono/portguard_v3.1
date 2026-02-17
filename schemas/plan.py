from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class PlanCreate(BaseModel):
    plan_name: str
    plan_type: str

class PlanUpdate(BaseModel):
    plan_name: Optional[str] = None
    plan_type: Optional[str] = None
    status: Optional[str] = None

class PlanResponse(BaseModel):
    id: UUID
    plan_name: str
    plan_type: str
    status: str
    created_at: datetime
    created_by: Optional[UUID] = None
    model_config = ConfigDict(from_attributes=True)