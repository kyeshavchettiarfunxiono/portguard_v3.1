"""
Downtime tracking model for operational downtime cost analysis.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from enum import Enum

from core.database import Base


class DowntimeType(str, Enum):
    """Types of operational downtime."""
    MECHANICAL = "MECHANICAL"
    SYSTEM_FAILURE = "SYSTEM_FAILURE"
    WEATHER = "WEATHER"
    STAFFING = "STAFFING"
    CUSTOMS_DELAY = "CUSTOMS_DELAY"
    MANUAL_HOLD = "MANUAL_HOLD"


class Downtime(Base):
    """Track equipment/operational downtime and associated costs."""
    __tablename__ = "downtimes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    downtime_type = Column(SQLEnum(DowntimeType), nullable=False)
    reason = Column(String(500), nullable=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    duration_hours = Column(Float, default=0.0)
    hourly_rate = Column(Float, default=250.0)  # R250/hour
    cost_impact = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    container = relationship("Container", back_populates="downtime_events")
    
    def calculate_cost(self) -> dict:
        """Calculate duration and cost impact."""
        if self.end_time is None:
            return {
                "status": "ONGOING",
                "duration_hours": None,
                "cost_impact": None
            }
        
        duration = self.end_time - self.start_time
        self.duration_hours = duration.total_seconds() / 3600
        self.cost_impact = self.duration_hours * self.hourly_rate
        
        return {
            "status": "COMPLETED",
            "duration_hours": round(self.duration_hours, 2),
            "cost_impact": round(self.cost_impact, 2),
            "currency": "ZAR"
        }
