"""
Truck offloading model for export truck unloading workflows.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
import uuid

from sqlalchemy import DateTime, Enum, Integer, String, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from core.database import Base


class TruckOffloadingStatus(PyEnum):
    REGISTERED = "REGISTERED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"


class TruckOffloadingStep(PyEnum):
    ARRIVAL_PHOTOS = "ARRIVAL_PHOTOS"
    DAMAGE_ASSESSMENT = "DAMAGE_ASSESSMENT"
    OFFLOADING_PHOTOS = "OFFLOADING_PHOTOS"
    COMPLETION_PHOTOS = "COMPLETION_PHOTOS"
    DRIVER_SIGNOFF = "DRIVER_SIGNOFF"


class TruckOffloading(Base):
    __tablename__ = "truck_offloading"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    truck_registration: Mapped[str] = mapped_column(String(30), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(120), nullable=False)
    driver_license: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    transporter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    client: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_note_number: Mapped[str] = mapped_column(String(80), nullable=False)
    commodity_type: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    horse_registration: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[TruckOffloadingStatus] = mapped_column(
        Enum(TruckOffloadingStatus, native_enum=False),
        nullable=False,
        default=TruckOffloadingStatus.REGISTERED
    )
    current_step: Mapped[TruckOffloadingStep] = mapped_column(
        Enum(TruckOffloadingStep, native_enum=False),
        nullable=False,
        default=TruckOffloadingStep.ARRIVAL_PHOTOS
    )

    arrival_photos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    offloading_photos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    damage_photos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_photos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    damage_reported: Mapped[bool] = mapped_column(Boolean, default=False)
    damage_type: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    damage_severity: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    damage_location: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    damage_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    damage_signoff_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    damage_signoff_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    damage_signoff_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    damage_assessment_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    signoff_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    signoff_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    variance_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    modified_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
