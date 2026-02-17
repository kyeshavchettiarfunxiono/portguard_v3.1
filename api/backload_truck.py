"""
API endpoints for backload truck packing workflows.
"""
from pathlib import Path
from typing import Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.backload_truck import BackloadTruckStep, BackloadTruckStatus
from schemas.backload_truck import (
    BackloadTruckCreate,
    BackloadTruckResponse,
    BackloadCargoItemCreate,
    BackloadCargoItemResponse,
    BackloadManifestUpdate,
    BackloadTruckSignoff
)
from services.backload_truck_service import BackloadTruckService

router = APIRouter(prefix="/api/backload-trucks", tags=["backload-trucks"])


@router.post("/", response_model=BackloadTruckResponse)
def register_backload_truck(
    payload: BackloadTruckCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return BackloadTruckService.create_truck(payload, db, cast(UUID, current_user.id))


@router.get("/", response_model=list[BackloadTruckResponse])
def list_backload_trucks(
    status: Optional[BackloadTruckStatus] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return BackloadTruckService.list_trucks(db, status)


@router.get("/{truck_id}", response_model=BackloadTruckResponse)
def get_backload_truck(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return BackloadTruckService.get_truck(truck_id, db)


@router.post("/{truck_id}/start", response_model=BackloadTruckResponse)
def start_backload_truck(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = BackloadTruckService.get_truck(truck_id, db)
    return BackloadTruckService.start_packing(truck, cast(UUID, current_user.id), db)


@router.post("/{truck_id}/photo-upload")
async def upload_backload_photo(
    truck_id: UUID,
    step: BackloadTruckStep,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images allowed.")

    max_size = 10 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    upload_dir = Path(f"uploads/backload_trucks/{truck_id}/{step.value}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = file.filename or "photo.jpg"
    file_path = upload_dir / filename
    file_path.write_bytes(contents)

    truck = BackloadTruckService.get_truck(truck_id, db)
    BackloadTruckService.record_photo(truck, step, db)

    return {
        "status": "success",
        "message": f"Photo uploaded for {step.value}",
        "file_path": str(file_path)
    }


@router.post("/{truck_id}/manifest/items", response_model=BackloadCargoItemResponse)
def add_manifest_item(
    truck_id: UUID,
    payload: BackloadCargoItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = BackloadTruckService.get_truck(truck_id, db)
    return BackloadTruckService.add_manifest_item(truck, payload, db)


@router.post("/{truck_id}/manifest", response_model=BackloadTruckResponse)
def update_manifest(
    truck_id: UUID,
    payload: BackloadManifestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = BackloadTruckService.get_truck(truck_id, db)
    return BackloadTruckService.update_manifest(truck, payload, db)


@router.post("/{truck_id}/advance-step", response_model=BackloadTruckResponse)
def advance_step(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = BackloadTruckService.get_truck(truck_id, db)
    return BackloadTruckService.advance_step(truck, db)


@router.post("/{truck_id}/revert-step", response_model=BackloadTruckResponse)
def revert_step(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = BackloadTruckService.get_truck(truck_id, db)
    return BackloadTruckService.revert_step(truck, db)


@router.post("/{truck_id}/signoff", response_model=BackloadTruckResponse)
def signoff(
    truck_id: UUID,
    payload: BackloadTruckSignoff,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = BackloadTruckService.get_truck(truck_id, db)
    return BackloadTruckService.sign_off(truck, payload.driver_name, db)


@router.post("/{truck_id}/complete", response_model=BackloadTruckResponse)
def complete_backload_truck(
    truck_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    truck = BackloadTruckService.get_truck(truck_id, db)
    return BackloadTruckService.complete(truck, cast(UUID, current_user.id), db)
