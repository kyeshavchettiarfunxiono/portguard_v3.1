from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class ContainerPlan(Base):
    __tablename__ = "container_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    stack_priority = Column(Integer, nullable=False, default=3)
    yard_zone = Column(String(120), nullable=True)
    planned_date = Column(DateTime(timezone=True), nullable=True)
    plan_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    modified_by = Column(UUID(as_uuid=True), nullable=True)
