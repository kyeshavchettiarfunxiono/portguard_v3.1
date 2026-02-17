"""
Container SQLAlchemy model with strict state transitions and audit trails.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 
# Docker Configured & new project directory has been created for this version on github at the following link: 


from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    JSON,
    UniqueConstraint,
    Integer,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
from typing import Optional, TYPE_CHECKING, cast, List
import uuid

from core.database import Base


class ContainerType(PyEnum):
    """Enum for container types."""
    TWENTY_FT = "20FT"
    FORTY_FT = "40FT"
    HC = "HC"


class ContainerStatus(PyEnum):
    """Enum for container status with strict state transition rules."""
    REGISTERED = "REGISTERED"
    PACKING = "PACKING"
    UNPACKING = "UNPACKING"
    PENDING_REVIEW = "PENDING_REVIEW"
    FINALIZED = "FINALIZED"


# State transition rules: which states can transition to which
VALID_STATE_TRANSITIONS = {
    ContainerStatus.REGISTERED: [
        ContainerStatus.PACKING,
        ContainerStatus.UNPACKING,
    ],
    ContainerStatus.PACKING: [
        ContainerStatus.PENDING_REVIEW,
    ],
    ContainerStatus.UNPACKING: [
        ContainerStatus.PENDING_REVIEW,
    ],
    ContainerStatus.PENDING_REVIEW: [
        ContainerStatus.FINALIZED,
        ContainerStatus.PACKING,  # Allow reversion for corrections
        ContainerStatus.UNPACKING,  # Allow reversion for corrections
    ],
    ContainerStatus.FINALIZED: [],  # Terminal state
}


class Container(Base):
    """
    Container model representing physical containers in the logistics system.
    
    Supports strict state transitions and maintains audit trails for tracking
    who created the container and who last modified it.
    """
    __tablename__ = "containers"
    
    __table_args__ = (
        UniqueConstraint("container_no", name="uq_container_no"),
    )
    
    # Primary Key
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        doc="Unique identifier for the container"
    )
    
    # Container Information
    container_no = Column(
        String(11),
        nullable=False,
        unique=True,
        doc="Unique container number (11 characters, typically ISO 6346 format)"
    )
    
    type = Column(
        Enum(ContainerType, native_enum=False), 
        nullable=False,
        doc="Container type (20FT, 40FT, or HC)"
    )
    
    status = Column(
        Enum(ContainerStatus, native_enum=False),
        nullable=False,
        default=ContainerStatus.REGISTERED,
        doc="Current container status"
    )
    
    # Physical Properties
    seal_no = Column(
        String(50),
        nullable=True,
        doc="Seal number for container security"
    )
    
    gross_mass = Column(
        Float,
        nullable=True,
        doc="Gross mass of container including contents (kg)"
    )
    
    tare_weight = Column(
        Float,
        nullable=True,
        doc="Tare weight of empty container (kg)"
    )

    # Client References (Export Packing)
    client = Column(
        String(50),
        nullable=True,
        doc="Client name associated with the container"
    )

    client_reference = Column(
        JSON,
        nullable=True,
        doc="Client-specific reference data (RE numbers, HEXP number)"
    )

    notes = Column(
        Text,
        nullable=True,
        doc="Additional packing notes or instructions"
    )
    
    # FCL Import-Specific Fields
    cargo_type = Column(
        String(100),
        nullable=True,
        doc="Type of cargo (e.g., Groupage Cargo, Steel, Automotive)"
    )
    
    arrival_date = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Date when container arrived at port"
    )
    
    unpacking_location = Column(
        String(200),
        nullable=True,
        doc="Location where container will be unpacked (e.g., Warehouse 1, Bay 5)"
    )
    
    # Foreign Keys
    booking_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the booking this container belongs to"
    )
    
    # Audit Trail - Creation
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Timestamp when container was created"
    )
    
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User ID who created the container"
    )
    
    # Audit Trail - Last Modification
    modified_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc="Timestamp of last modification"
    )
    
    modified_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User ID who last modified the container"
    )
    
    # Repair Tracking
    needs_repair = Column(Boolean, default=False, doc="Flag for containers needing repair")
    repair_notes = Column(String(1000), nullable=True, doc="Details about required repairs")
    
    # Relationships (Tier 2/3 features)
    booking = relationship("Booking", back_populates="containers")
    downtime_events = relationship("Downtime", back_populates="container")
    cargo_items = relationship("CargoItem", back_populates="container")
    packing_session = relationship("PackingSession", back_populates="container", uselist=False)
    unpacking_session = relationship("UnpackingSession", back_populates="container", uselist=False)
    
    def can_transition_to(self, new_status: ContainerStatus) -> bool:
        # Cast self.status to ContainerStatus to satisfy Pylance
        current_status = cast(ContainerStatus, self.status)
        if new_status not in VALID_STATE_TRANSITIONS.get(current_status, []):
            return False
        return True
    
    def transition_to(self, new_status: ContainerStatus, user_id: Optional[uuid.UUID] = None) -> bool:
        current_status = cast(ContainerStatus, self.status)
        if not self.can_transition_to(new_status):
            valid_transitions = VALID_STATE_TRANSITIONS.get(current_status, [])
            raise ValueError(
                f"Cannot transition from {current_status.value} to {new_status.value}. "
                f"Valid transitions: {[s.value for s in valid_transitions]}"
            )
        
        self.status = new_status
        self.modified_at = datetime.utcnow()
        if user_id:
            self.modified_by = user_id
        
        return True
    
    def get_valid_next_states(self) -> List[ContainerStatus]:
        current_status = cast(ContainerStatus, self.status)
        return VALID_STATE_TRANSITIONS.get(current_status, [])
    
    @property
    def vessel_name(self) -> Optional[str]:
        """Get vessel name from associated booking."""
        if self.booking:
            return self.booking.vessel_name
        return None
    
    def __repr__(self) -> str:
        """String representation of container."""
        return (
            f"<Container(id={self.id}, container_no={self.container_no}, "
            f"type={self.type.value}, status={self.status.value})>"
        )
