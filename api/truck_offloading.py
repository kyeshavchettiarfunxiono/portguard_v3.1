"""
API endpoints for truck offloading workflows.
"""
from pathlib import Path
from typing import Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.truck_offloading import TruckOffloadingStep, TruckOffloadingStatus
from schemas.truck_offloading import (
    TruckOffloadingCreate,
    TruckOffloadingDamageAssessmentComplete,
    TruckOffloadingDamageReport,
    TruckOffloadingItemCreate,
    TruckOffloadingItemResponse,
    TruckOffloadingResponse,
    TruckOffloadingSignoff
)
from services.truck_offloading_service import TruckOffloadingService

router = APIRouter(prefix="/api/truck-offloading", tags=["truck-offloading"])


@router.post("/", response_model=TruckOffloadingResponse)
def register_truck_offloading(
    payload: TruckOffloadingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return TruckOffloadingService.create_truck_offloading(payload, db, cast(UUID, current_user.id))


@router.get("/", response_model=list[TruckOffloadingResponse])
def list_truck_offloading(
    status: Optional[TruckOffloadingStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return TruckOffloadingService.list_trucks(db, status)


@router.get("/{truck_id}", response_model=TruckOffloadingResponse)
def get_truck_offloading(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return TruckOffloadingService.get_truck(truck_id, db)


@router.post("/{truck_id}/start", response_model=TruckOffloadingResponse)
def start_offloading(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = TruckOffloadingService.get_truck(truck_id, db)
    return TruckOffloadingService.start_offloading(truck, cast(UUID, current_user.id), db)


@router.post("/{truck_id}/photo-upload")
async def upload_truck_photo(
    truck_id: UUID,
    step: TruckOffloadingStep,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    allowed_types = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'video/mp4',
        'video/webm',
        'video/quicktime'
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images allowed.")

    max_size = 50 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    upload_dir = Path(f"uploads/truck_offloading/{truck_id}/{step.value}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = file.filename or "photo.jpg"
    file_path = upload_dir / filename
    file_path.write_bytes(contents)

    truck = TruckOffloadingService.get_truck(truck_id, db)
    if not file.content_type.startswith('video/'):
        TruckOffloadingService.record_photo(truck, step, db)

    return {
        "status": "success",
        "message": f"Photo uploaded for {step.value}",
        "file_path": str(file_path)
    }


@router.post("/{truck_id}/offloading-items", response_model=TruckOffloadingItemResponse)
def add_offloading_item(
    truck_id: UUID,
    payload: TruckOffloadingItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = TruckOffloadingService.get_truck(truck_id, db)
    return TruckOffloadingService.add_offloading_item(truck, payload, db)


@router.post("/{truck_id}/advance-step", response_model=TruckOffloadingResponse)
def advance_step(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = TruckOffloadingService.get_truck(truck_id, db)
    return TruckOffloadingService.advance_step(truck, db)


@router.post("/{truck_id}/revert-step", response_model=TruckOffloadingResponse)
def revert_step(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = TruckOffloadingService.get_truck(truck_id, db)
    return TruckOffloadingService.revert_step(truck, db)


@router.post("/{truck_id}/damage-report", response_model=TruckOffloadingResponse)
def report_damage(
    truck_id: UUID,
    payload: TruckOffloadingDamageReport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = TruckOffloadingService.get_truck(truck_id, db)
    return TruckOffloadingService.report_damage(
        truck,
        payload.damage_type,
        payload.severity,
        payload.location,
        payload.description,
        db
    )


@router.post("/{truck_id}/damage-assessment/complete", response_model=TruckOffloadingResponse)
def complete_damage_assessment(
    truck_id: UUID,
    payload: TruckOffloadingDamageAssessmentComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = TruckOffloadingService.get_truck(truck_id, db)
    return TruckOffloadingService.complete_damage_assessment(
        truck,
        payload.driver_name,
        payload.driver_comments,
        db
    )


@router.post("/{truck_id}/signoff", response_model=TruckOffloadingResponse)
def signoff(
    truck_id: UUID,
    payload: TruckOffloadingSignoff,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = TruckOffloadingService.get_truck(truck_id, db)
    return TruckOffloadingService.sign_off(
        truck,
        payload.driver_name,
        payload.actual_quantity,
        payload.variance_notes,
        db
    )


@router.post("/{truck_id}/complete", response_model=TruckOffloadingResponse)
def complete_offloading(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = TruckOffloadingService.get_truck(truck_id, db)
    return TruckOffloadingService.complete(truck, cast(UUID, current_user.id), db)
