from __future__ import annotations

import uuid
from datetime import datetime, date

from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class ContainerPlanningEntry(Base):
    __tablename__ = "container_planning_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    planning_date = Column(Date, nullable=False, index=True)
    booking_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    booking_reference = Column(String(120), nullable=True)
    vessel_name = Column(String(160), nullable=False)
    client_name = Column(String(120), nullable=False)
    container_type = Column(String(40), nullable=False)
    planned_quantity = Column(Integer, nullable=False, default=1)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    modified_by = Column(UUID(as_uuid=True), nullable=True)
