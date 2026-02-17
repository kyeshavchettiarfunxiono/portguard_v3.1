from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from core.database import Base


class TransnetVesselStack(Base):
    __tablename__ = "transnet_vessel_stacks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vessel_name = Column(String(120), nullable=False)
    voyage_number = Column(String(40), nullable=True)
    terminal = Column(String(80), nullable=True)
    berth = Column(String(40), nullable=True)
    eta = Column(DateTime(timezone=True), nullable=True)
    etd = Column(DateTime(timezone=True), nullable=True)
    stack_open = Column(DateTime(timezone=True), nullable=True)
    stack_close = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(40), nullable=True)
    pdf_source_url = Column(String(512), nullable=True)
    row_hash = Column(String(64), nullable=False, index=True, unique=True)
    last_updated = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class TransnetIngestRun(Base):
    __tablename__ = "transnet_ingest_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(20), nullable=False, default="manual")
    source_url = Column(String(512), nullable=True)
    status = Column(String(20), nullable=False, default="running")
    total_rows = Column(Integer, nullable=False, default=0)
    inserted = Column(Integer, nullable=False, default=0)
    updated = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class TransnetIngestRow(Base):
    __tablename__ = "transnet_ingest_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("transnet_ingest_runs.id"), nullable=False)
    row_hash = Column(String(64), nullable=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class TransnetBookingQueue(Base):
    __tablename__ = "transnet_booking_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vessel_name = Column(String(120), nullable=False)
    voyage_number = Column(String(40), nullable=True)
    terminal = Column(String(80), nullable=True)
    berth = Column(String(40), nullable=True)
    eta = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    row_hash = Column(String(64), nullable=False, unique=True, index=True)
    source_run_id = Column(Integer, ForeignKey("transnet_ingest_runs.id"), nullable=True)
    pdf_source_url = Column(String(512), nullable=True)
    booking_id = Column(UUID(as_uuid=True), nullable=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    declined_by = Column(UUID(as_uuid=True), nullable=True)
    declined_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
