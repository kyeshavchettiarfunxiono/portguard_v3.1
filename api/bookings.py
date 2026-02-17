# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from core.database import get_db
from core.security import get_current_user
from models.user import User
from api.dependencies import require_management, require_admin
from models.booking import Booking
from schemas.booking import BookingCreate, BookingResponse

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("/", response_model=list[BookingResponse])
def list_bookings(
    client: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List bookings, optionally filtered by client."""
    query = db.query(Booking)
    if client:
        query = query.filter(Booking.client == client)
    return query.order_by(Booking.created_at.desc()).all()


@router.post("/", response_model=BookingResponse)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management)
):
    """Create a new booking (Supervisor/Admin only)."""
    existing = db.query(Booking).filter(Booking.booking_reference == booking.booking_reference).first()
    if existing:
        raise HTTPException(status_code=409, detail="Booking reference already exists")

    new_booking = Booking(
        booking_reference=booking.booking_reference,
        client=booking.client,
        vessel_name=booking.vessel_name,
        container_type=booking.container_type
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
