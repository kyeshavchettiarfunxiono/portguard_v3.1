from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class OperationalIncident(Base):
    __tablename__ = "operational_incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(160), nullable=False)
    incident_type = Column(String(80), nullable=False)
    priority = Column(String(40), nullable=False)
    location = Column(String(160), nullable=True)
    reporter_name = Column(String(120), nullable=True)
    incident_at = Column(DateTime(timezone=True), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class OperationalIncidentPhoto(Base):
    __tablename__ = "operational_incident_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey("operational_incidents.id"), nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
