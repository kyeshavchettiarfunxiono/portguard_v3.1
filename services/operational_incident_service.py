import uuid
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from models.operational_incident import OperationalIncident, OperationalIncidentPhoto

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def parse_incident_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid incident date/time") from exc


def validate_images(photos: Iterable[UploadFile]) -> None:
    for photo in photos:
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail="Invalid file type. Only PNG/JPG allowed.")
        contents = photo.file.read()
        if len(contents) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
        photo.file.seek(0)


def save_incident_photos(incident_id: uuid.UUID, photos: Iterable[UploadFile]) -> list[OperationalIncidentPhoto]:
    upload_dir = Path("uploads") / "operational_incidents" / str(incident_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved: list[OperationalIncidentPhoto] = []

    for photo in photos:
        filename = photo.filename or f"incident_{uuid.uuid4()}.jpg"
        safe_name = f"{uuid.uuid4()}_{Path(filename).name}"
        file_path = upload_dir / safe_name
        with file_path.open("wb") as buffer:
            buffer.write(photo.file.read())

        saved.append(OperationalIncidentPhoto(incident_id=incident_id, file_path=str(file_path)))

    return saved


def build_photo_url(file_path: str) -> str:
    normalized = file_path.replace("\\", "/").strip()
    if "/uploads/" in normalized:
        suffix = normalized.split("/uploads/", 1)[1]
        return f"/uploads/{suffix}"
    if normalized.startswith("uploads/"):
        return f"/{normalized}"
    return f"/uploads/{Path(normalized).name}"


class OperationalIncidentService:
    @staticmethod
    def create_report(
        title: str,
        incident_type: str,
        priority: str,
        incident_at: datetime,
        description: str,
        location: Optional[str],
        reporter_name: Optional[str],
        photos: Optional[list[UploadFile]],
        db: Session,
    ) -> OperationalIncident:
        if len(description.strip()) < 50:
            raise HTTPException(status_code=400, detail="Description must be at least 50 characters")

        incident = OperationalIncident(
            title=title.strip(),
            incident_type=incident_type.strip(),
            priority=priority.strip(),
            location=(location or "").strip() or None,
            reporter_name=(reporter_name or "").strip() or None,
            incident_at=incident_at,
            description=description.strip(),
        )
        db.add(incident)
        db.commit()
        db.refresh(incident)

        if photos:
            validate_images(photos)
            saved_photos = save_incident_photos(uuid.UUID(str(incident.id)), photos)
            for photo in saved_photos:
                db.add(photo)
            db.commit()
            db.refresh(incident)

        return incident

    @staticmethod
    def list_reports(db: Session) -> list[OperationalIncident]:
        return db.query(OperationalIncident).order_by(OperationalIncident.incident_at.desc()).all()

    @staticmethod
    def get_report(report_id: uuid.UUID, db: Session) -> OperationalIncident:
        report = db.query(OperationalIncident).filter(OperationalIncident.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Incident report not found")
        return report

    @staticmethod
    def serialize_report(report: OperationalIncident, db: Session) -> dict:
        photos = (
            db.query(OperationalIncidentPhoto)
            .filter(OperationalIncidentPhoto.incident_id == report.id)
            .order_by(OperationalIncidentPhoto.uploaded_at.desc())
            .all()
        )
        return {
            "id": report.id,
            "title": report.title,
            "incident_type": report.incident_type,
            "priority": report.priority,
            "location": report.location,
            "reporter_name": report.reporter_name,
            "incident_at": report.incident_at,
            "description": report.description,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
            "photos": [
                {
                    "id": photo.id,
                    "url": build_photo_url(str(photo.file_path)),
                    "uploaded_at": photo.uploaded_at,
                }
                for photo in photos
            ],
        }
