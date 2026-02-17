from datetime import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from core.database import Base


class DamageReport(Base):
    __tablename__ = "damage_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=False)
    container_no = Column(String(20), nullable=False)

    damage_type = Column(String(80), nullable=False)
    severity = Column(String(20), nullable=False)
    location = Column(String(120), nullable=True)
    description = Column(Text, nullable=False)

    photo_count = Column(Integer, nullable=False, default=0)
    needs_repair = Column(Boolean, nullable=False, default=False)
    is_resolved = Column(Boolean, nullable=False, default=False)
    resolved_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    reported_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reported_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    photos = relationship("DamageReportPhoto", cascade="all, delete-orphan")


class DamageReportPhoto(Base):
    __tablename__ = "damage_report_photos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("damage_reports.id"), nullable=False)
    file_path = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
