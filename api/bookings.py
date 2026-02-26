# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from uuid import UUID

from core.database import get_db
from core.security import get_current_user
from models.user import User
from api.dependencies import require_management, require_admin
from models.booking import Booking
from schemas.booking import BookingCreate, BookingResponse
from services.config_service import get_booking_clients

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/", response_model=list[BookingResponse])
def list_bookings(
    client: Optional[str] = None,
    booking_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List bookings, optionally filtered by client."""
    query = db.query(Booking)
    if client:
        normalized_client = client.strip().upper().replace(" ", "_")
        query = query.filter(func.upper(Booking.client) == normalized_client)
    if booking_type:
        normalized_type = booking_type.strip().upper()
        if normalized_type not in {"EXPORT", "IMPORT"}:
            raise HTTPException(status_code=400, detail="Invalid booking_type")
        query = query.filter(Booking.booking_type == normalized_type)
    return query.order_by(Booking.created_at.desc()).all()


@router.get("/client-options")
def list_booking_client_options(
    booking_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized_type = booking_type.strip().upper()
    if normalized_type not in {"EXPORT", "IMPORT"}:
        raise HTTPException(status_code=400, detail="Invalid booking_type")

    existing = (
        db.query(Booking.client)
        .filter(Booking.booking_type == normalized_type)
        .group_by(Booking.client)
        .order_by(func.lower(Booking.client))
        .all()
    )
    existing_clients = [str(row[0]).strip() for row in existing if row and row[0]]

    configured_clients = get_booking_clients(normalized_type)
    merged_clients = sorted(set(existing_clients + configured_clients), key=lambda item: item.lower())
    return {"booking_type": normalized_type, "clients": merged_clients}


@router.post("/", response_model=BookingResponse)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management)
):
    """Create a new booking (Supervisor/Admin only)."""
    booking_type = str(booking.booking_type or "EXPORT").strip().upper()
    if booking_type not in {"EXPORT", "IMPORT"}:
        raise HTTPException(status_code=400, detail="Invalid booking_type")

    category = str(booking.category).strip().upper() if booking.category else None
    if booking_type == "IMPORT" and category and category not in {"FCL", "GRP"}:
        raise HTTPException(status_code=400, detail="Invalid category. Use FCL or GRP")

    normalized_client = str(booking.client or "").strip().upper().replace(" ", "_")
    if not normalized_client:
        raise HTTPException(status_code=400, detail="Client is required")

    normalized_reference = str(booking.booking_reference or "").strip().upper()
    if not normalized_reference:
        raise HTTPException(status_code=400, detail="Booking reference is required")

    existing = (
        db.query(Booking)
        .filter(func.upper(Booking.booking_reference) == normalized_reference)
        .first()
    )
    if existing:
        same_scope = (
            str(existing.client or "").strip().upper() == normalized_client
            and str(existing.booking_type or "").strip().upper() == booking_type
        )
        if same_scope:
            return existing
        raise HTTPException(
            status_code=409,
            detail="Booking reference already exists for a different client or type"
        )

    new_booking = Booking(
        booking_reference=normalized_reference,
        booking_type=booking_type,
        client=normalized_client,
        vessel_name=booking.vessel_name,
        voyage_number=booking.voyage_number,
        arrival_voyage=booking.arrival_voyage,
        date_in_depot=booking.date_in_depot,
        container_type=booking.container_type,
        category=category,
        notes=booking.notes,
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)
    return new_booking


@router.delete("/{booking_id}")
def delete_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """Delete a booking (Admin only)."""
    try:
        booking_uuid = UUID(booking_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid booking ID format")

    booking = db.query(Booking).filter(Booking.id == booking_uuid).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db.delete(booking)
    db.commit()
    return {"message": "Booking deleted successfully"}
