from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from core.database import Base
import enum

class PlanStatus(enum.Enum):
    DRAFT = "DRAFT"
    LOCKED = "LOCKED"
    COMPLETED = "COMPLETED"

class Plan(Base):
    __tablename__ = "plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    vessel_name = Column(String, nullable=False)
    planned_quantity = Column(Integer, default=0)
    planned_date = Column(DateTime, nullable=False)
    status = Column(Enum(PlanStatus), default=PlanStatus.DRAFT)
    
    # Audit Fields
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))