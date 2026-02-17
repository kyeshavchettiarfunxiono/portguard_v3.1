"""
Backload truck packing model for export truck workflows.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List
import uuid

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class BackloadTruckStatus(PyEnum):
    REGISTERED = "REGISTERED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PAUSED = "PAUSED"


class BackloadTruckStep(PyEnum):
    BEFORE_PHOTOS = "BEFORE_PHOTOS"
    MANIFEST_WEIGHTS = "MANIFEST_WEIGHTS"
    PACKING_PHOTOS = "PACKING_PHOTOS"
    AFTER_PHOTOS = "AFTER_PHOTOS"
    DRIVER_SIGNOFF = "DRIVER_SIGNOFF"


class BackloadTruck(Base):
    __tablename__ = "backload_trucks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    truck_registration: Mapped[str] = mapped_column(String(30), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(120), nullable=False)
    transporter_name: Mapped[str] = mapped_column(String(120), nullable=False)
    client: Mapped[str] = mapped_column(String(120), nullable=False)
    cargo_type: Mapped[str] = mapped_column(String(120), nullable=False)
    cargo_description: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_destination: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)

    horse_registration: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    driver_license: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    delivery_note_number: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    gross_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[BackloadTruckStatus] = mapped_column(
        Enum(BackloadTruckStatus, native_enum=False),
        nullable=False,
        default=BackloadTruckStatus.REGISTERED
    )
    current_step: Mapped[BackloadTruckStep] = mapped_column(
        Enum(BackloadTruckStep, native_enum=False),
        nullable=False,
        default=BackloadTruckStep.BEFORE_PHOTOS
    )

    before_photos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    packing_photos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    after_photos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    total_cargo_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    transfer_order_number: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    signoff_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    signoff_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    modified_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    items: Mapped[List[BackloadCargoItem]] = relationship(
        "BackloadCargoItem",
        back_populates="truck",
        cascade="all, delete-orphan"
    )


class BackloadCargoItem(Base):
    __tablename__ = "backload_cargo_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    truck_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("backload_trucks.id", ondelete="CASCADE"))

    description: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    truck: Mapped[BackloadTruck] = relationship("BackloadTruck", back_populates="items")
