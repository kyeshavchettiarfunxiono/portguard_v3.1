from datetime import datetime
import json
import uuid

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)  # type: ignore
    reference = Column(String(40), unique=True, index=True, nullable=False)  # type: ignore
    event_time = Column(DateTime(timezone=True), default=datetime.utcnow, index=True, nullable=False)  # type: ignore
    level = Column(String(16), index=True, nullable=False, default="INFO")  # type: ignore
    category = Column(String(64), index=True, nullable=False, default="system")  # type: ignore
    action = Column(String(160), nullable=False)  # type: ignore
    message = Column(Text, nullable=True)  # type: ignore

    actor_id = Column(UUID(as_uuid=True), nullable=True)  # type: ignore
    actor_email = Column(String(255), index=True, nullable=True)  # type: ignore
    actor_role = Column(String(32), index=True, nullable=True)  # type: ignore

    request_id = Column(String(64), index=True, nullable=True)  # type: ignore
    endpoint = Column(String(255), index=True, nullable=True)  # type: ignore
    http_method = Column(String(12), index=True, nullable=True)  # type: ignore
    status_code = Column(Integer, index=True, nullable=True)  # type: ignore
    ip_address = Column(String(64), nullable=True)  # type: ignore
    metadata_json = Column(Text, nullable=True)  # type: ignore

    @property
    def metadata_dict(self) -> dict:
        raw_value = getattr(self, "metadata_json", None)
        if raw_value is None:
            return {}
        try:
            raw_text = str(raw_value)
            if not raw_text:
                return {}
            payload = json.loads(raw_text)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
        return {}
