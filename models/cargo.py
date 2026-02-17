"""
Cargo manifest model for unpacking operations.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum

from core.database import Base


class CargoCondition(str, Enum):
    """Physical condition of cargo."""
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    DAMAGED = "DAMAGED"
    MISSING = "MISSING"


class CargoItem(Base):
    """Cargo items unpacked from containers."""
    __tablename__ = "cargo_items"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=False)
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit = Column(String(50), nullable=False)
    condition = Column(SQLEnum(CargoCondition), default=CargoCondition.GOOD)
    notes = Column(String(1000), nullable=True)
    recorded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    container = relationship("Container", back_populates="cargo_items")
    inspector = relationship("User")
