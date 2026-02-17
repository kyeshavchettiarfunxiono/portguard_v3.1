# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import cast
from datetime import datetime

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.container import ContainerStatus
from services.container_service import ContainerService
from services.evidence_service import EvidenceService

router = APIRouter(prefix="/containers", tags=["packing"])


@router.post("/{container_id}/start-packing")
def start_packing(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Begin packing workflow for a container."""
    container = ContainerService.get_container(container_id, db)
    
    current_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
    if current_status != ContainerStatus.REGISTERED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start packing. Current status: {current_status}"
        )
    
    container.transition_to(ContainerStatus.PACKING, cast(UUID, current_user.id))
    db.commit()
    return {"status": "PACKING", "message": "Packing workflow started"}


@router.post("/{container_id}/complete-packing")
def complete_packing(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete packing and move to review.
    Validates photo evidence before transition.
    """
    container = ContainerService.get_container(container_id, db)
    
    current_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
    if current_status != ContainerStatus.PACKING.value:
        raise HTTPException(
            status_code=400,
            detail=f"Container must be in PACKING status. Current: {current_status}"
        )
    
    validation = EvidenceService.validate_evidence(container_id, db)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Missing photos: {validation['missing_types']}"
        )
    
    container.transition_to(ContainerStatus.PENDING_REVIEW, cast(UUID, current_user.id))
    db.commit()
    return {"status": "PENDING_REVIEW", "message": "Packing complete"}


@router.post("/{container_id}/close-packing")
def close_container_after_packing(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Close container after packing (State Machine enforced).
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
        "message": "Container closed after packing with all photo evidence validated",
        "validated_photos": closure_check["validation_status"]["uploaded_photos"]
    }


@router.get("/{container_id}/packing-readiness")
def check_packing_readiness(
    container_id: str,
    db: Session = Depends(get_db)
):
    """Check if container is ready to close after packing."""
    return EvidenceService.can_close_container(container_id, db)