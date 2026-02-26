from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    id: UUID
    reference: str
    event_time: datetime
    level: str
    category: str
    action: str
    message: str | None
    actor_id: UUID | None
    actor_email: str | None
    actor_role: str | None
    request_id: str | None
    endpoint: str | None
    http_method: str | None
    status_code: int | None
    ip_address: str | None
    metadata: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    total: int
    count: int
    logs: list[AuditLogResponse]
