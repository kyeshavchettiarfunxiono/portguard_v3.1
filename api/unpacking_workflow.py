# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, cast as py_cast
from datetime import datetime
import os
import shutil
from pathlib import Path
from pydantic import BaseModel

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.unpacking import UnpackingSession
from models.container import Container, ContainerStatus
from services.unpacking_service import UnpackingService
from services.cargo_service import CargoService
from schemas.unpacking import UnpackingSessionResponse, UnpackingProgressResponse

router = APIRouter(prefix="/api/unpacking", tags=["unpacking"])

class CargoItemRequest(BaseModel):
    description: str
    quantity: int
    unit: str
    condition: str
    notes: Optional[str] = None


class ManifestDetailsRequest(BaseModel):
    document_reference: Optional[str] = None
    manifest_notes: Optional[str] = None


@router.post("/{container_id}/start", response_model=UnpackingSessionResponse)
def start_unpacking_workflow(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start unpacking workflow for a container."""
    # Get or create unpacking session
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")

    if bool(container.needs_repair):
        raise HTTPException(status_code=400, detail="Container blocked due to damage. Complete repair before unpacking.")
    
    # Transition container to UNPACKING status
    current_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
    if current_status != ContainerStatus.UNPACKING.value:
        user_id = py_cast(UUID, current_user.id)
        container.transition_to(ContainerStatus.UNPACKING, user_id)
        db.commit()
    
    # Get or create unpacking session
    session = UnpackingService.get_or_create_unpacking_session(
        container_id,
        db,
        inspector_id=py_cast(UUID, current_user.id)
    )
    session.inspector_id = py_cast(UUID, current_user.id)  # type: ignore
    session.started_at = session.started_at or container.modified_at  # type: ignore
    db.commit()
    db.refresh(session)
    
    return session


@router.get("/{container_id}/progress", response_model=UnpackingProgressResponse)
def get_unpacking_progress(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get unpacking progress for a container."""
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    session = db.query(UnpackingSession).filter(
        UnpackingSession.container_id == container_id
    ).first()
    
    if not session:
        # Create new session if doesn't exist
        session = UnpackingService.get_or_create_unpacking_session(
            container_id,
            db,
            inspector_id=py_cast(UUID, current_user.id)
        )
    
    # Get container type for requirements
    container_type = py_cast(str, container.type.value if hasattr(container.type, 'value') else str(container.type))
    container_no = py_cast(str, container.container_no)
    requirements = session.get_required_photos()
    
    return UnpackingProgressResponse(
        container_id=container_id,
        container_no=container_no,
        container_type=container_type,
        current_step=py_cast(str, session.current_step.value),
        is_complete=py_cast(bool, session.is_complete),
        exterior_inspection_photos=py_cast(int, session.exterior_inspection_photos or 0),
        door_opening_photos=py_cast(int, session.door_opening_photos or 0),
        interior_inspection_photos=py_cast(int, session.interior_inspection_photos or 0),
        cargo_unloading_photos=py_cast(int, session.cargo_unloading_photos or 0),
        exterior_required=py_cast(int, requirements.get('EXTERIOR_INSPECTION', 1)),
        door_required=py_cast(int, requirements.get('DOOR_OPENING', 1)),
        interior_required=py_cast(int, requirements.get('INTERIOR_INSPECTION', 2)),
        cargo_required=py_cast(int, requirements.get('CARGO_UNLOADING', 2)),
        manifest_required=py_cast(int, requirements.get('CARGO_MANIFEST', 0)),
        cargo_unloading_started_at=py_cast(Optional[datetime], session.cargo_unloading_started_at),
        cargo_unloading_completed_at=py_cast(Optional[datetime], session.cargo_unloading_completed_at),
        cargo_unloading_duration_minutes=py_cast(Optional[int], session.cargo_unloading_duration_minutes),
        damage_reported=py_cast(bool, session.damage_reported),
        damage_description=py_cast(Optional[str], session.damage_description),
        cargo_items_count=py_cast(int, session.cargo_items_count or 0),
        manifest_complete=py_cast(bool, session.manifest_complete),
        manifest_document_reference=py_cast(Optional[str], session.manifest_document_reference),
        manifest_notes=py_cast(Optional[str], session.manifest_notes),
        manifest_documented_at=py_cast(Optional[datetime], session.manifest_documented_at),
    )


@router.post("/{container_id}/photo-upload")
def upload_unpacking_photo(
    container_id: UUID,
    step: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload photo for unpacking step."""
    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images allowed.")
    
    # Check file size (10MB limit)
    max_size = 10 * 1024 * 1024
    contents = file.file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
    
    # Save file
    upload_dir = Path(f"uploads/{container_id}/unpacking/{step}")
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    filename = py_cast(str, file.filename if file.filename else "photo.jpg")
    file_path = upload_dir / filename
    with open(file_path, 'wb') as f:
        f.write(contents)
    
    # Record photo in session
    session = UnpackingService.record_photo(container_id, step, db)
    
    return {
        "status": "success",
        "message": f"Photo uploaded for {step}",
        "file_path": str(file_path),
        "current_photos": getattr(session, f'{step.lower()}_photos', 0)
    }


@router.post("/{container_id}/advance-step", response_model=UnpackingSessionResponse)
def advance_unpacking_step(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Move to next unpacking step."""
    session = UnpackingService.advance_step(container_id, db)
    return session


@router.post("/{container_id}/revert-step", response_model=UnpackingSessionResponse)
def revert_unpacking_step(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revert to previous unpacking step."""
    session = UnpackingService.revert_to_previous_step(container_id, db)
    return session


@router.post("/{container_id}/cargo-item")
def add_cargo_item(
    container_id: str,
    cargo_req: CargoItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record a cargo item in manifest."""
    # Handle Optional[str] and UUID type safety
    notes_val: str = cargo_req.notes if cargo_req.notes is not None else ""
    inspector_id = py_cast(UUID, current_user.id)
    
    return CargoService.record_cargo_item(
        container_id=container_id,
        description=cargo_req.description,
        quantity=cargo_req.quantity,
        unit=cargo_req.unit,
        condition=cargo_req.condition,
        notes=notes_val,
        inspector_id=inspector_id,
        db=db
    )


@router.post("/{container_id}/damage-report")
def report_damage(
    container_id: UUID,
    description: str,
    damage_photo_count: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Report damage or discrepancies during unpacking."""
    session = UnpackingService.report_damage(
        container_id,
        description,
        damage_photo_count,
        db
    )
    return {
        "status": "success",
        "message": "Damage reported",
        "damage_reported": session.damage_reported
    }


@router.post("/{container_id}/manifest-details", response_model=UnpackingSessionResponse)
def document_manifest_details(
    container_id: UUID,
    payload: ManifestDetailsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record import manifest header/reference details once cargo lines are captured."""
    session = UnpackingService.document_manifest(
        container_id=container_id,
        document_reference=payload.document_reference,
        manifest_notes=payload.manifest_notes,
        inspector_id=py_cast(UUID, current_user.id),
        db=db,
    )
    return session


@router.post("/{container_id}/complete", response_model=UnpackingSessionResponse)
def complete_unpacking_workflow(
    container_id: UUID,
    final_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete unpacking workflow."""
    user_id = py_cast(UUID, current_user.id)
    session = UnpackingService.complete_unpacking(
        container_id,
        final_notes,
        user_id,
        db
    )
    
    # Transition container to PENDING_REVIEW
    container = db.query(Container).filter(Container.id == container_id).first()
    if container:
        current_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
        if current_status != ContainerStatus.PENDING_REVIEW.value:
            container.transition_to(ContainerStatus.PENDING_REVIEW, user_id)
            db.commit()
        
    return session

@router.get("/{container_id}/manifest")
def get_full_cargo_manifest(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve complete cargo manifest for container."""
    return CargoService.get_cargo_manifest(container_id, db)


@router.get("/{container_id}/damage-report")
def get_damage_report(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get damage/loss report for container."""
    return CargoService.get_damaged_cargo_report(container_id, db)
