"""
Packing workflow model to track container packing progress through all 4 steps.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, cast as py_cast
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


class PackingStep(PyEnum):
    """Enum for packing workflow steps."""
    BEFORE_PACKING = "BEFORE_PACKING"
    CARGO_PHOTOS = "CARGO_PHOTOS"
    AFTER_PACKING = "AFTER_PACKING"
    SEALING = "SEALING"


class PackingSession(Base):
    """
    Tracks the packing workflow session for a container.
    One session per container, progresses through 4 steps.
    """
    __tablename__ = "packing_sessions"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    container_id = Column(
        UUID(as_uuid=True),
        ForeignKey("containers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        doc="Reference to the container being packed"
    )
    
    # Current workflow state
    current_step = Column(
        Enum(PackingStep, native_enum=False),
        nullable=False,
        default=PackingStep.BEFORE_PACKING,
        doc="Current packing step (1-4)"
    )
    
    # Photo counts per step
    before_packing_photos = Column(Integer, default=0, doc="Count of before packing photos")
    cargo_photos = Column(Integer, default=0, doc="Count of cargo photos")
    after_packing_photos = Column(Integer, default=0, doc="Count of after packing photos")
    
    # Sealing information
    seal_number = Column(String(100), nullable=True, doc="Applied seal number")
    seal_photo_count = Column(Integer, default=0, doc="Count of seal photos")
    gross_mass = Column(String(50), nullable=True, doc="Container gross mass in kg")
    tare_weight = Column(String(50), nullable=True, doc="Container tare weight in kg")
    
    # Session tracking
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by = Column(UUID(as_uuid=True), nullable=True, doc="User who completed packing")
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    container = relationship("Container", back_populates="packing_session")
    
    def get_required_photos(self, container_type: str) -> dict:
        """Get required photo counts based on container type."""
        return {
            'BEFORE_PACKING': 5 if container_type in ['40FT', 'HC'] else 4,
            'CARGO_PHOTOS': 2,
            'AFTER_PACKING': 2,
            'SEALING': 1
        }
    
    def is_step_complete(self, container_type: str) -> bool:
        """Check if current step has met photo requirements."""
        required = self.get_required_photos(container_type)
        current_step = py_cast(PackingStep, self.current_step)
        step_name = current_step.value
        
        photo_map = {
            'BEFORE_PACKING': self.before_packing_photos,
            'CARGO_PHOTOS': self.cargo_photos,
            'AFTER_PACKING': self.after_packing_photos,
            'SEALING': self.seal_photo_count
        }
        
        current_count = photo_map.get(step_name, 0)
        return current_count >= required.get(step_name, 1)
    
    def can_move_to_next_step(self, container_type: str) -> bool:
        """Check if current step is complete and can advance."""
        current_step = py_cast(PackingStep, self.current_step)
        if current_step == PackingStep.SEALING:
            return self.is_step_complete(container_type) and bool(self.seal_number)
        return self.is_step_complete(container_type)
    
    def move_to_next_step(self) -> bool:
        """Advance to next step in workflow."""
        step_order = [
            PackingStep.BEFORE_PACKING,
            PackingStep.CARGO_PHOTOS,
            PackingStep.AFTER_PACKING,
            PackingStep.SEALING
        ]
        
        current_step = py_cast(PackingStep, self.current_step)
        current_index = step_order.index(current_step)
        if current_index < len(step_order) - 1:
            self.current_step = step_order[current_index + 1]
            return True
        return False
    
    def __repr__(self) -> str:
        return f"<PackingSession(container_id={self.container_id}, step={self.current_step.value})>"
