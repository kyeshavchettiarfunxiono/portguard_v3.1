from datetime import datetime
import os

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.dependencies import require_admin
from core.database import get_db
from schemas.audit_log import AuditLogListResponse
from services.audit_service import AuditService

router = APIRouter(prefix="/admin/audit", tags=["audit"], dependencies=[Depends(require_admin)])


def _max_limit() -> int:
    return int(os.getenv("AUDIT_LOG_MAX_LIMIT", "200"))


@router.get("/logs", response_model=AuditLogListResponse)
def list_audit_logs(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    level: str | None = Query(default=None),
    category: str | None = Query(default=None),
    actor_email: str | None = Query(default=None),
    endpoint_contains: str | None = Query(default=None),
    status_code: int | None = Query(default=None, ge=100, le=599),
    from_time: datetime | None = Query(default=None),
    to_time: datetime | None = Query(default=None),
    request_id: str | None = Query(default=None),
):
    bounded_limit = min(limit, _max_limit())
    total, logs = AuditService.list_logs(
        db,
        limit=bounded_limit,
        offset=offset,
        level=level,
        category=category,
        actor_email=actor_email,
        endpoint_contains=endpoint_contains,
        status_code=status_code,
        from_time=from_time,
        to_time=to_time,
        request_id=request_id,
    )

    return {
        "total": total,
        "count": len(logs),
        "logs": [
            {
                "id": item.id,
                "reference": item.reference,
                "event_time": item.event_time,
                "level": item.level,
                "category": item.category,
                "action": item.action,
                "message": item.message,
                "actor_id": item.actor_id,
                "actor_email": item.actor_email,
                "actor_role": item.actor_role,
                "request_id": item.request_id,
                "endpoint": item.endpoint,
                "http_method": item.http_method,
                "status_code": item.status_code,
                "ip_address": item.ip_address,
                "metadata": item.metadata_dict,
            }
            for item in logs
        ],
    }


@router.post("/prune")
def prune_audit_logs(db: Session = Depends(get_db)):
    deleted = AuditService.prune_old_logs(db)
    return {"deleted": deleted}
