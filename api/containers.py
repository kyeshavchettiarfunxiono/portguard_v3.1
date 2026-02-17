# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, cast as sql_cast, String
from uuid import UUID
from typing import cast, Optional
from datetime import datetime
from pydantic import BaseModel
from fastapi.responses import Response, FileResponse

from core.database import get_db
from core.security import get_current_user
from models.user import User
from api.dependencies import require_supervisor
from models.container import Container, ContainerStatus
from models.downtime import Downtime
from models.unpacking import UnpackingSession
from schemas.container import ContainerCreate, ContainerResponse, ContainerUpdate
from services.container_service import ContainerService
from services.evidence_service import EvidenceService
from services.pdf_service import generate_container_pdf
from services.reporting_service import ReportingService
from models.evidence import ContainerImage

router = APIRouter(prefix="/containers", tags=["containers"])


class DowntimeRequest(BaseModel):
    downtime_type: str
    reason: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None


@router.post("/", response_model=ContainerResponse)
def create_container(
    container: ContainerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Register a new container."""
    return ContainerService.create_container(container, cast(UUID, current_user.id), db)


@router.get("/", response_model=list[ContainerResponse])
def list_containers(db: Session = Depends(get_db)):
    """List all containers."""
    return ContainerService.list_containers(db)


@router.get("/{container_id}", response_model=ContainerResponse)
def get_container(
    container_id: str,
    db: Session = Depends(get_db)
):
    """Get container details."""
    return ContainerService.get_container(container_id, db)


@router.put("/{container_id}/status", response_model=ContainerResponse)
def update_container_status(
    container_id: str,
    payload: ContainerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update container status with evidence enforcement for review."""
    if payload.status is None:
        raise HTTPException(status_code=400, detail="Status is required")

    if payload.status == ContainerStatus.PENDING_REVIEW:
        validation = EvidenceService.validate_evidence(container_id, db)
        if not validation["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Missing photos: {validation['missing_types']}"
            )

    return ContainerService.transition_container_status(
        container_id,
        payload.status,
        cast(UUID, current_user.id),
        db
    )


@router.post("/{container_id}/upload-image/")
async def upload_container_image(
    container_id: str,
    image_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload evidence photo for container."""
    return EvidenceService.upload_container_image(container_id, image_type, file, cast(UUID, current_user.id), db)


@router.get("/{container_id}/verify-evidence")
def verify_container_evidence(
    container_id: str,
    db: Session = Depends(get_db)
):
    """Check if container has all required photos."""
    return EvidenceService.validate_evidence(container_id, db)


@router.get("/{container_id}/evidence-gallery")
def get_evidence_gallery(
    container_id: str,
    db: Session = Depends(get_db)
):
    """Get gallery of uploaded evidence photos."""
    return ContainerService.get_container_evidence(container_id, db)


@router.post("/{container_id}/finalize-arrival", response_model=ContainerResponse)
def finalize_container_arrival(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor)
):
    """Finalize container arrival (supervisor only)."""
    # Validate evidence before finalizing
    validation = EvidenceService.validate_evidence(container_id, db)
    if not validation["is_valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Missing photos: {validation['missing_types']}"
        )
    
    return ContainerService.finalize_container(container_id, cast(UUID, current_user.id), db)


@router.get("/{container_id}/export-pdf")
def export_container_pdf(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Export container arrival certificate as PDF."""
    container = ContainerService.get_container(container_id, db)
    
    container_status = container.status.value if hasattr(container.status, 'value') else str(container.status)
    if container_status != ContainerStatus.FINALIZED.value:
        raise HTTPException(
            status_code=400,
            detail=f"Container not finalized. Current: {container_status}"
        )
    
    images = db.query(ContainerImage).filter(
        ContainerImage.container_id == container.id
    ).all()
    
    pdf_output = generate_container_pdf(
        container_data={
            "container_no": container.container_no,
            "status": container_status,
            "id": container_id
        },
        images=images
    )
    
    if pdf_output is None:
        raise HTTPException(status_code=500, detail="Failed to generate PDF")
    
    return Response(
        content=bytes(pdf_output),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Cert_{container.container_no}.pdf"}
    )


@router.get("/{container_id}/report")
def export_container_report(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor)
):
    """Export supervisor audit PDF summary for a container."""
    file_path = ReportingService.generate_summary_pdf(container_id, db)
    filename = f"Report_{container_id}.pdf"
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )


@router.get("/vessel-bookings/priority-alerts")
def get_priority_vessel_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get vessel bookings with priority alerts for imminent stacking."""
    bookings = ContainerService.get_vessel_bookings_with_priority(db)
    critical_count = sum(1 for b in bookings if b["priority_alert"])
    
    return {
        "total_bookings": len(bookings),
        "critical_alerts": critical_count,
        "bookings": bookings
    }


@router.post("/{container_id}/downtime/log")
def log_container_downtime(
    container_id: str,
    downtime_req: DowntimeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Log downtime event and calculate cost impact."""
    return ContainerService.resolve_downtime(
        container_id=container_id,
        downtime_type=downtime_req.downtime_type,
        reason=downtime_req.reason,
        start_time=downtime_req.start_time,
          end_time=downtime_req.end_time,
          user_id=cast(UUID, current_user.id),
          db=db
    )


@router.get("/{container_id}/downtime/summary")
def get_downtime_summary(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get downtime summary and cost impact for container."""
    return ContainerService.get_container_downtime_summary(container_id, db)


@router.get("/stats")
def get_container_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dashboard statistics for containers."""
    try:
        total = db.query(Container).count()
        pending = db.query(Container).filter(
            Container.status == ContainerStatus.PENDING_REVIEW  # type: ignore
        ).count()
        repairs = db.query(Container).filter(
            Container.needs_repair.is_(True)
        ).count()
        
        return {
            "total": total,
            "pending": pending,
            "repairs": repairs
        }
    except Exception as e:
        return {
            "total": 0,
            "pending": 0,
            "repairs": 0,
            "error": str(e)
        }


@router.get("/supervisor/dashboard")
def get_supervisor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor)
):
    """Supervisor dashboard - RLS filtered to PENDING_REVIEW and Needs Repair only."""
    # ROW-LEVEL SECURITY: Only PENDING_REVIEW or flagged as needs_repair
    containers = db.query(Container).filter(
        or_(
            sql_cast(Container.status, String) == ContainerStatus.PENDING_REVIEW.value,
            Container.needs_repair.is_(True)
        )
    ).order_by(desc(Container.modified_at)).all()  # type: ignore
    
    dashboard_data = []
    
    for container in containers:
        container_dict = {
            "id": str(container.id),
            "container_no": container.container_no,
            "status": container.status.value if hasattr(container.status, 'value') else str(container.status),
            "needs_repair": container.needs_repair or False,
            "repair_notes": container.repair_notes,
            "container_type": container.type.value if hasattr(container.type, 'value') else str(container.type),
            "created_at": container.created_at.isoformat(),
            "modified_at": container.modified_at.isoformat(),
        }
        dashboard_data.append(container_dict)
    
    return {
        "supervisor_id": str(current_user.id),
        "total_containers": len(dashboard_data),
        "pending_review_count": sum(1 for c in dashboard_data if c["status"] == "PENDING_REVIEW"),
        "needs_repair_count": sum(1 for c in dashboard_data if c["needs_repair"]),
        "containers": dashboard_data
    }


@router.get("/supervisor/alerts")
def get_supervisor_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor)
):
    """Return containers with active downtime or damage reports plus cost summary."""
    now = datetime.utcnow()

    active_downtime = db.query(Downtime).filter(Downtime.end_time.is_(None)).all()
    active_downtime_ids = {dt.container_id for dt in active_downtime}

    damage_sessions = db.query(UnpackingSession).filter(UnpackingSession.damage_reported.is_(True)).all()
    damaged_container_ids = {sess.container_id for sess in damage_sessions}

    damaged_flagged_ids = {
        c.id for c in db.query(Container).filter(Container.needs_repair.is_(True)).all()
    }

    alert_container_ids = active_downtime_ids | damaged_container_ids | damaged_flagged_ids
    if not alert_container_ids:
        return {
            "total_alerts": 0,
            "containers": []
        }

    containers = db.query(Container).filter(Container.id.in_(alert_container_ids)).all()
    response = []

    for container in containers:
        downtimes = db.query(Downtime).filter(Downtime.container_id == container.id).all()
        total_cost = 0.0
        active_count = 0

        for dt in downtimes:
            if dt.end_time is None:
                active_count += 1
                duration_hours = (now - dt.start_time).total_seconds() / 3600
                hourly_rate = cast(float, dt.hourly_rate) if dt.hourly_rate is not None else 250.0
                total_cost += duration_hours * hourly_rate  # type: ignore[operator]
            else:
                total_cost += cast(float, dt.cost_impact) if dt.cost_impact is not None else 0.0

        unpacking = db.query(UnpackingSession).filter(UnpackingSession.container_id == container.id).first()
        has_damage = bool(container.needs_repair) or bool(unpacking and unpacking.damage_reported)

        response.append({
            "container_id": str(container.id),
            "container_no": container.container_no,
            "status": container.status.value if hasattr(container.status, 'value') else str(container.status),
            "client": container.client,
            "active_downtime_count": active_count,
            "total_cost_impact_zar": round(float(total_cost), 2),
            "has_damage_report": has_damage,
            "damage_description": getattr(unpacking, "damage_description", None),
            "needs_repair": bool(container.needs_repair)
        })

    return {
        "total_alerts": len(response),
        "containers": response
    }


@router.post("/{container_id}/resolve-issue")
def resolve_container_issue(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor)
):
    """Supervisor resolves damage/repair flags after inspection."""
    container = ContainerService.get_container(container_id, db)

    container.needs_repair = False  # type: ignore
    container.repair_notes = None  # type: ignore
    container.modified_at = datetime.utcnow()
    container.modified_by = cast(UUID, current_user.id)

    session = db.query(UnpackingSession).filter(UnpackingSession.container_id == container.id).first()
    if session:
        session.damage_reported = False  # type: ignore
        session.damage_description = None  # type: ignore
        session.damage_photo_count = 0  # type: ignore

    db.commit()

    return {
        "container_id": str(container.id),
        "resolved": True,
        "resolved_by": str(current_user.id),
        "resolved_at": container.modified_at.isoformat()
    }


@router.post("/{container_id}/finalize", response_model=ContainerResponse)
def finalize_container_review(
    container_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor)
):
    """Supervisor final approval gate (PENDING_REVIEW -> FINALIZED)."""
    return ContainerService.finalize_container(container_id, cast(UUID, current_user.id), db)


@router.post("/{container_id}/flag-repair")
def flag_container_for_repair(
    container_id: str,
    repair_reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_supervisor)
):
    """Flag container as needing repair (Supervisor only)."""
    container = ContainerService.get_container(container_id, db)
    container.needs_repair = True  # type: ignore
    container.repair_notes = repair_reason  # type: ignore
    container.modified_at = datetime.utcnow()
    db.commit()
    db.refresh(container)
    
    return {
        "container_id": container_id,
        "flagged_for_repair": True,
        "reason": repair_reason,
        "flagged_by": str(current_user.id),
        "flagged_at": container.modified_at.isoformat()
    }
