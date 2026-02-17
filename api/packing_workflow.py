"""
API endpoints for packing workflow management.
"""
from uuid import UUID
# Software Engineer: Kyeshav Chettiar 
import time
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from typing import cast as py_cast
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.container import Container, ContainerStatus
from models.packing import PackingStep
from models.evidence import ContainerImage
from schemas.packing import PackingSessionResponse, SealingRequest, PhotoUploadRequest
from services.packing_service import PackingService
from services.evidence_service import EvidenceService

router = APIRouter(prefix="/packing", tags=["packing"])


@router.post("/start/{container_id}", response_model=PackingSessionResponse)
def start_packing(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start or resume packing session for a container."""
    # Verify container exists and belongs to accessible client
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    if bool(container.needs_repair):
        raise HTTPException(status_code=400, detail="Container blocked due to damage. Complete repair before packing.")
    
    # Transition container to PACKING status if not already
    current_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
    if current_status != ContainerStatus.PACKING.value:
        user_id = py_cast(UUID, current_user.id)
        container.transition_to(ContainerStatus.PACKING, user_id)
        db.commit()

    # Get or create packing session
    session = PackingService.get_or_create_packing_session(container_id, db)
    return session


@router.get("/{container_id}/progress", response_model=dict)
def get_packing_progress(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed progress for current packing step."""
    return PackingService.get_step_progress(container_id, db)


@router.get("/{container_id}/session", response_model=PackingSessionResponse)
def get_packing_session(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current packing session details."""
    session = PackingService.get_packing_session(container_id, db)
    return session


@router.post("/photo-upload/{container_id}")
async def upload_packing_photo(
    container_id: UUID,
    step: PackingStep,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and store packing photos for a container step."""
    # Verify container exists
    container = db.query(Container).filter(Container.id == container_id).first()
    if not container:
        raise HTTPException(status_code=404, detail="Container not found")
    
    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="File must have a filename")
    
    # Validate file type
    allowed_extensions = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"File type .{file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}")
    
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    try:
        # Create upload directory structure
        upload_dir = Path("uploads") / str(container_id) / step.value.lower()
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(time.time() * 1000)
        filename = f"{step.value}_{timestamp}.{file_ext}"
        file_path = upload_dir / filename
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        # Store image record in database
        image_record = ContainerImage(
            container_id=container_id,
            file_path=str(file_path),
            image_type=step.value
        )
        db.add(image_record)
        db.commit()
        
        # Update photo count in packing session
        session = PackingService.record_photos(container_id, step, 1, db)
        
        return {
            'status': 'success',
            'message': f'Photo uploaded for {step.value}',
            'step': step.value,
            'file_path': str(file_path),
            'image_id': str(image_record.id),
            'session': PackingSessionResponse.model_validate(session)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")


@router.get("/{container_id}/photos")
def list_packing_photos(
    container_id: UUID,
    step: PackingStep,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List packing photos for a container step."""
    images = db.query(ContainerImage).filter(
        ContainerImage.container_id == container_id,
        ContainerImage.image_type == step.value
    ).order_by(ContainerImage.uploaded_at.desc()).all()

    photos = []
    for image in images:
        file_path = Path(image.file_path)
        if not file_path.exists():
            continue
        rel_path = file_path.as_posix()
        url = f"/uploads/{rel_path.replace('uploads/', '')}"
        photos.append({
            "id": str(image.id),
            "url": url,
            "uploaded_at": image.uploaded_at.isoformat() if image.uploaded_at else None
        })

    return {"photos": photos}


@router.delete("/{container_id}/photos/{photo_id}")
def delete_packing_photo(
    container_id: UUID,
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a packing photo for a container and update counts."""
    image = db.query(ContainerImage).filter(
        ContainerImage.id == photo_id,
        ContainerImage.container_id == container_id
    ).first()

    if not image:
        raise HTTPException(status_code=404, detail="Photo not found")

    step = None
    try:
        step = PackingStep(image.image_type)
    except ValueError:
        step = None

    if step:
        session = PackingService.get_packing_session(container_id, db)
        if step == PackingStep.BEFORE_PACKING:
            session.before_packing_photos = max((session.before_packing_photos or 0) - 1, 0)  # type: ignore
        elif step == PackingStep.CARGO_PHOTOS:
            session.cargo_photos = max((session.cargo_photos or 0) - 1, 0)  # type: ignore
        elif step == PackingStep.AFTER_PACKING:
            session.after_packing_photos = max((session.after_packing_photos or 0) - 1, 0)  # type: ignore
        elif step == PackingStep.SEALING:
            session.seal_photo_count = max((session.seal_photo_count or 0) - 1, 0)  # type: ignore

    file_path = Path(image.file_path)
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass

    db.delete(image)
    db.commit()

    return {"status": "deleted"}


@router.post("/advance-step/{container_id}", response_model=PackingSessionResponse)
def advance_packing_step(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Advance to next step if current step is complete."""
    session = PackingService.advance_step(container_id, db)
    return session


@router.post("/seal/{container_id}", response_model=PackingSessionResponse)
def seal_container(
    container_id: UUID,
    request: SealingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Complete packing by sealing container."""
    validation = EvidenceService.validate_evidence(str(request.container_id), db)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Missing photos: {validation['missing_types']}"
        )

    user_id = py_cast(UUID, current_user.id)
    session = PackingService.complete_packing(
        container_id=request.container_id,
        seal_number=request.seal_number,
        gross_mass=request.gross_mass,
        tare_weight=request.tare_weight,
        user_id=user_id,
        db=db
    )
    
    # Transition container to PENDING_REVIEW upon successful sealing
    container = db.query(Container).filter(Container.id == request.container_id).first()
    if container:
        current_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
        if current_status != ContainerStatus.PENDING_REVIEW.value:
            container.transition_to(ContainerStatus.PENDING_REVIEW, user_id)
            db.commit()
        
    return session


@router.get("/{container_id}/can-advance")
def check_can_advance(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if container can advance to next step."""
    can_advance = PackingService.can_advance_step(container_id, db)
    return {'can_advance': can_advance}


@router.post("/{container_id}/pause")
def pause_and_release(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause packing session and release container for handover. All progress is saved."""
    result = PackingService.pause_and_release(container_id, db)
    return result

@router.post("/revert-step/{container_id}", response_model=PackingSessionResponse)
def revert_step(
    container_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Revert to previous step in packing workflow."""
    session = PackingService.revert_to_previous_step(container_id, db)
    return session