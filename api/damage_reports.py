from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.user import User
from schemas.damage_report import DamageReportResponse, DamageReportUpdateRequest, DamageReportResolveRequest
from services.damage_report_service import DamageReportService

router = APIRouter(prefix="/damage-reports", tags=["damage-reports"])


@router.get("/", response_model=list[DamageReportResponse])
def list_damage_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    reports = DamageReportService.list_reports(db)
    return [DamageReportService.serialize_report(report, db) for report in reports]


@router.post("/", response_model=DamageReportResponse)
def create_damage_report(
    container_id: Optional[str] = Form(None),
    container_no: Optional[str] = Form(None),
    booking_id: Optional[str] = Form(None),
    damage_type: str = Form(...),
    severity: str = Form(...),
    location: Optional[str] = Form(None),
    description: str = Form(...),
    photos: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    user_id = UUID(str(current_user.id))
    report = DamageReportService.create_report(
        container_id=container_id,
        container_no=container_no,
        booking_id=booking_id,
        damage_type=damage_type,
        severity=severity,
        location=location,
        description=description,
        photos=photos,
        db=db,
        user_id=user_id
    )
    return DamageReportService.serialize_report(report, db)


@router.get("/{report_id}", response_model=DamageReportResponse)
def get_damage_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = DamageReportService.get_report(report_id, db)
    return DamageReportService.serialize_report(report, db)


@router.put("/{report_id}", response_model=DamageReportResponse)
def update_damage_report(
    report_id: UUID,
    payload: DamageReportUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = DamageReportService.get_report(report_id, db)
    updated = DamageReportService.update_report(
        report=report,
        damage_type=payload.damage_type,
        severity=payload.severity,
        location=payload.location,
        description=payload.description,
        db=db
    )
    return DamageReportService.serialize_report(updated, db)


@router.post("/{report_id}/photos", response_model=DamageReportResponse)
def add_damage_report_photos(
    report_id: UUID,
    photos: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = DamageReportService.get_report(report_id, db)
    updated = DamageReportService.add_photos(report, photos, db)
    return DamageReportService.serialize_report(updated, db)


@router.delete("/{report_id}/photos/{photo_id}", response_model=DamageReportResponse)
def delete_damage_report_photo(
    report_id: UUID,
    photo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = DamageReportService.get_report(report_id, db)
    updated = DamageReportService.delete_photo(report, photo_id, db)
    return DamageReportService.serialize_report(updated, db)


@router.post("/{report_id}/resolve", response_model=DamageReportResponse)
def resolve_damage_report(
    report_id: UUID,
    payload: DamageReportResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = DamageReportService.get_report(report_id, db)
    user_id = UUID(str(current_user.id))
    resolved = DamageReportService.resolve_report(report, user_id, payload.notes, db)
    return DamageReportService.serialize_report(resolved, db)


@router.post("/{report_id}/reopen", response_model=DamageReportResponse)
def reopen_damage_report(
    report_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = DamageReportService.get_report(report_id, db)
    reopened = DamageReportService.reopen_report(report, db)
    return DamageReportService.serialize_report(reopened, db)
