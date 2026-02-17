"""
Unpacking session model for import container unpacking operations.
"""
from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum

from core.database import Base


class UnpackingStep(str, Enum):
    """Unpacking workflow steps."""
    EXTERIOR_INSPECTION = "EXTERIOR_INSPECTION"
    DOOR_OPENING = "DOOR_OPENING"
    INTERIOR_INSPECTION = "INTERIOR_INSPECTION"
    CARGO_UNLOADING = "CARGO_UNLOADING"
    CARGO_MANIFEST = "CARGO_MANIFEST"
    FINAL_INSPECTION = "FINAL_INSPECTION"


class UnpackingSession(Base):
    """Tracking unpacking workflow progress for import containers."""
    __tablename__ = "unpacking_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=False, unique=True)
    
    # Workflow progress
    current_step = Column(SQLEnum(UnpackingStep), default=UnpackingStep.EXTERIOR_INSPECTION)
    is_complete = Column(Boolean, default=False)
    
    # Photo counts per step
    exterior_inspection_photos = Column(Integer, default=0)
    door_opening_photos = Column(Integer, default=0)
    interior_inspection_photos = Column(Integer, default=0)
    cargo_unloading_photos = Column(Integer, default=0)
    
    # Damage/Discrepancy tracking
    damage_reported = Column(Boolean, default=False)
    damage_description = Column(String(2000), nullable=True)
    damage_photo_count = Column(Integer, default=0)
    
    # Cargo manifest
    cargo_items_count = Column(Integer, default=0)
    manifest_complete = Column(Boolean, default=False)
    
    # Final inspection notes
    final_notes = Column(String(2000), nullable=True)
    inspector_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    container = relationship("Container", back_populates="unpacking_session")
    inspector = relationship("User")
    
    def get_required_photos(self, step: Optional[str] = None) -> dict:
        """Get required photo counts per step. Standard: 2-3 photos per step."""
        photo_requirements = {
            'EXTERIOR_INSPECTION': 3,      # Exterior condition from multiple angles
            'DOOR_OPENING': 2,             # Door condition and seal
            'INTERIOR_INSPECTION': 3,      # Interior condition from multiple angles
            'CARGO_UNLOADING': 2,          # Loading/unloading process
            'CARGO_MANIFEST': 1,           # Manifest document
            'FINAL_INSPECTION': 2          # Final state
        }
        
        if step:
            return {step: photo_requirements.get(step, 1)}
        return photo_requirements
    
    def is_step_complete(self) -> bool:
        """Check if current step has met photo requirements."""
        from typing import cast as py_cast
        current_step = py_cast(str, self.current_step.value if hasattr(self.current_step, 'value') else str(self.current_step))
        required = self.get_required_photos(current_step).get(current_step, 1)
        
        step_photo_map = {
            'EXTERIOR_INSPECTION': py_cast(int, self.exterior_inspection_photos or 0),
            'DOOR_OPENING': py_cast(int, self.door_opening_photos or 0),
            'INTERIOR_INSPECTION': py_cast(int, self.interior_inspection_photos or 0),
            'CARGO_UNLOADING': py_cast(int, self.cargo_unloading_photos or 0),
            'CARGO_MANIFEST': py_cast(int, self.cargo_items_count or 0),
            'FINAL_INSPECTION': 1 if self.final_notes is not None else 0
        }
        
        current_photos = step_photo_map.get(current_step, 0)
        return current_photos >= required
    
    def can_move_to_next_step(self) -> bool:
        """Check if workflow can advance to next step."""
        # Must complete current step
        if not self.is_step_complete():
            return False
        
        # Special requirement for manifest step
        from typing import cast as py_cast
        current_step_val = py_cast(str, self.current_step.value if hasattr(self.current_step, 'value') else str(self.current_step))
        cargo_count = py_cast(int, self.cargo_items_count or 0)
        if current_step_val == 'CARGO_MANIFEST' and cargo_count == 0:
            return False
        
        return True
