from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from models.audit_log import AuditLog
from models.user import User


class AuditService:
    LEVELS = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}

    @staticmethod
    def generate_reference(at_time: datetime | None = None) -> str:
        timestamp = (at_time or datetime.utcnow()).strftime("%Y%m%d")
        return f"AUD-{timestamp}-{uuid4().hex[:8].upper()}"

    @staticmethod
    def _safe_level(level: str | None) -> str:
        normalized = (level or "INFO").strip().upper()
        return normalized if normalized in AuditService.LEVELS else "INFO"

    @staticmethod
    def create_log(
        db: Session,
        *,
        action: str,
        category: str = "system",
        level: str = "INFO",
        message: str | None = None,
        actor: User | None = None,
        request_id: str | None = None,
        endpoint: str | None = None,
        http_method: str | None = None,
        status_code: int | None = None,
        ip_address: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            reference=AuditService.generate_reference(),
            level=AuditService._safe_level(level),
            category=(category or "system").strip().lower(),
            action=action,
            message=message,
            actor_id=getattr(actor, "id", None),
            actor_email=getattr(actor, "email", None),
            actor_role=getattr(actor, "role", None),
            request_id=request_id,
            endpoint=endpoint,
            http_method=http_method,
            status_code=status_code,
            ip_address=ip_address,
            metadata_json=json.dumps(metadata or {}, default=str),
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def prune_old_logs(db: Session) -> int:
        retention_days = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "180"))
        cutoff = datetime.utcnow() - timedelta(days=retention_days)

        deleted = db.query(AuditLog).filter(AuditLog.event_time < cutoff).delete()  # type: ignore[arg-type]
        db.commit()
        return int(deleted or 0)

    @staticmethod
    def list_logs(
        db: Session,
        *,
        limit: int,
        offset: int,
        level: str | None = None,
        category: str | None = None,
        actor_email: str | None = None,
        endpoint_contains: str | None = None,
        status_code: int | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        request_id: str | None = None,
    ) -> tuple[int, list[AuditLog]]:
        query = db.query(AuditLog)

        if level:
            query = query.filter(AuditLog.level == level.strip().upper())
        if category:
            query = query.filter(AuditLog.category == category.strip().lower())
        if actor_email:
            query = query.filter(AuditLog.actor_email.ilike(f"%{actor_email.strip()}%"))
        if endpoint_contains:
            query = query.filter(AuditLog.endpoint.ilike(f"%{endpoint_contains.strip()}%"))
        if status_code is not None:
            query = query.filter(AuditLog.status_code == int(status_code))
        if from_time is not None:
            query = query.filter(AuditLog.event_time >= from_time)
        if to_time is not None:
            query = query.filter(AuditLog.event_time <= to_time)
        if request_id:
            query = query.filter(AuditLog.request_id == request_id.strip())

        total = query.count()
        logs = query.order_by(AuditLog.event_time.desc()).offset(offset).limit(limit).all()
        return total, logs


__all__ = ["AuditService"]
