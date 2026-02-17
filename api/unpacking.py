# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID
from typing import cast, Optional
from datetime import datetime
from pydantic import BaseModel

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.container import ContainerStatus
from services.container_service import ContainerService
from services.evidence_service import EvidenceService
from services.cargo_service import CargoService

router = APIRouter(prefix="/containers", tags=["unpacking"])


class CargoItemRequest(BaseModel):
    description: str
    quantity: int
    unit: str
    condition: str
    notes: Optional[str] = None


@router.post("/{container_id}/start-unpacking")
def start_unpacking(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Begin unpacking workflow for a container."""
    container = ContainerService.get_container(container_id, db)
    
    current_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
    if current_status != ContainerStatus.REGISTERED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start unpacking. Current status: {current_status}"
        )
    
    container.transition_to(ContainerStatus.UNPACKING, cast(UUID, current_user.id))
    db.commit()
    return {"status": "UNPACKING", "message": "Unpacking workflow started"}


@router.post("/{container_id}/complete-unpacking")
def complete_unpacking(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete unpacking and move to review."""
    container = ContainerService.get_container(container_id, db)
    
    current_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
    if current_status != ContainerStatus.UNPACKING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Container must be in UNPACKING status. Current: {current_status}"
        )
    
    validation = EvidenceService.validate_evidence(container_id, db)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Missing photos: {validation['missing_types']}"
        )
    
    container.transition_to(ContainerStatus.PENDING_REVIEW, cast(UUID, current_user.id))
    db.commit()
    return {"status": "PENDING_REVIEW", "message": "Unpacking complete"}


@router.post("/{container_id}/close-unpacking")
def close_container_after_unpacking(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Close container after unpacking (State Machine enforced).
    BLOCKED unless all mandatory photos are confirmed.
    """
    # STATE MACHINE ENFORCEMENT
    closure_check = EvidenceService.can_close_container(container_id, db)
    
    if not closure_check["can_close"]:
        raise HTTPException(
            status_code=409,
            detail=closure_check["message"]
        )
    
    container = ContainerService.get_container(container_id, db)
    container.modified_at = datetime.utcnow()
    container.modified_by = cast(UUID, current_user.id)
    db.commit()
    
    return {
        "status": "success",
        "container_id": container_id,
        "message": "Container closed after unpacking with all photo evidence validated",
        "validated_photos": closure_check["validation_status"]["uploaded_photos"]
    }


@router.get("/{container_id}/unpacking-readiness")
def check_unpacking_readiness(
    container_id: str,
    db: Session = Depends(get_db)
):
    """Check if container is ready to close after unpacking."""
    return EvidenceService.can_close_container(container_id, db)


@router.post("/{container_id}/manifest/record-item")
def record_cargo_manifest_item(
    container_id: str,
    cargo_req: CargoItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Record unpacked cargo item in manifest."""
    # FIX: Handle Optional[str] and UUID type safety
    notes_val: str = cargo_req.notes if cargo_req.notes is not None else ""
    from typing import cast as typing_cast
    inspector_id = typing_cast(UUID, current_user.id)
    
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


@router.get("/{container_id}/manifest")
def get_full_cargo_manifest(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve complete cargo manifest for container."""
    return CargoService.get_cargo_manifest(container_id, db)


@router.get("/{container_id}/manifest/damage-report")
def get_damage_report(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get damage/loss report for container."""
    return CargoService.get_damaged_cargo_report(container_id, db)