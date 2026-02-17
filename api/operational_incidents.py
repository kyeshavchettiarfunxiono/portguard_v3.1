from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas.operational_incident import OperationalIncidentResponse
from services.operational_incident_service import OperationalIncidentService, parse_incident_datetime

router = APIRouter(prefix="/operational-incidents", tags=["operational-incidents"])


@router.get("/", response_model=list[OperationalIncidentResponse])
def list_incidents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    reports = OperationalIncidentService.list_reports(db)
    return [OperationalIncidentService.serialize_report(report, db) for report in reports]


@router.post("/", response_model=OperationalIncidentResponse)
def create_incident(
    title: str = Form(...),
    incident_type: str = Form(...),
    priority: str = Form(...),
    incident_at: str = Form(...),
    description: str = Form(...),
    location: Optional[str] = Form(None),
    reporter_name: Optional[str] = Form(None),
    photos: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    parsed_date = parse_incident_datetime(incident_at)
    report = OperationalIncidentService.create_report(
        title=title,
        incident_type=incident_type,
        priority=priority,
        incident_at=parsed_date,
        description=description,
        location=location,
        reporter_name=reporter_name or str(current_user.username),
        photos=photos,
        db=db,
    )
    return OperationalIncidentService.serialize_report(report, db)


@router.get("/{report_id}", response_model=OperationalIncidentResponse)
def get_incident(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = OperationalIncidentService.get_report(report_id, db)
    return OperationalIncidentService.serialize_report(report, db)
