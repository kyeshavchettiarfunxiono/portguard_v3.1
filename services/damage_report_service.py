import uuid
from pathlib import Path
from datetime import datetime
from typing import Iterable, Optional, Tuple, cast

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from models.container import Container, ContainerType
from models.booking import Booking
from models.damage_report import DamageReport, DamageReportPhoto
from schemas.container import ContainerCreate
from services.container_service import ContainerService

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_SIZE = 10 * 1024 * 1024


def normalize_severity(value: str) -> str:
    return value.strip().upper()


def requires_repair(severity: str) -> bool:
    return normalize_severity(severity) in {"MAJOR", "CRITICAL"}


def map_booking_container_type(raw: str) -> ContainerType:
    value = (raw or "").upper()
    if "20" in value:
        return ContainerType.TWENTY_FT
    if "HC" in value or "HIGH" in value:
        return ContainerType.HC
    return ContainerType.FORTY_FT


def get_or_create_damage_holding_booking(db: Session) -> Booking:
    existing = db.query(Booking).filter(Booking.booking_reference == "DAMAGE_HOLDING").first()
    if existing:
        return existing

    booking = Booking(
        booking_reference="DAMAGE_HOLDING",
        booking_type="EXPORT",
        client="DAMAGE_HOLD",
        vessel_name="NO_VESSEL",
        voyage_number=None,
        arrival_voyage=None,
        date_in_depot=None,
        container_type="40FT",
        category=None,
        notes="System-generated holding booking for damaged grounded containers",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def resolve_container(
    container_id: Optional[str],
    container_no: Optional[str],
    booking_id: Optional[str],
    db: Session,
    user_id: Optional[uuid.UUID]
) -> Tuple[Container, bool]:
    if container_id:
        container = ContainerService.get_container(container_id, db)
        return container, False

    if not container_no:
        raise HTTPException(status_code=400, detail="Container number is required")

    existing = db.query(Container).filter(Container.container_no == container_no).first()
    if existing:
        return existing, False

    booking = None
    if booking_id:
        booking_uuid = uuid.UUID(booking_id)
        booking = db.query(Booking).filter(Booking.id == booking_uuid).first()
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
    else:
        booking = get_or_create_damage_holding_booking(db)

    container_type = map_booking_container_type(str(booking.container_type))
    payload = ContainerCreate(
        container_no=container_no,
        booking_id=cast(uuid.UUID, booking.id),
        type=container_type,
        seal_no=None,
        gross_mass=None,
        client=cast(str, booking.client),
        client_reference=None,
        notes=None,
        cargo_type=None,
        arrival_date=None,
        unpacking_location=None,
        manifest_vessel_name=None,
        manifest_voyage_number=None,
        depot_list_fcl_count=None,
        depot_list_grp_count=None,
    )
    container = ContainerService.create_container(payload, user_id, db)
    return container, True


def validate_images(photos: Iterable[UploadFile]) -> None:
    for photo in photos:
        if photo.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail="Invalid file type. Only images allowed.")
        contents = photo.file.read()
        if len(contents) > MAX_IMAGE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")
        photo.file.seek(0)


def save_damage_photos(report_id: uuid.UUID, photos: Iterable[UploadFile]) -> list[DamageReportPhoto]:
    upload_dir = Path("uploads") / "damage_reports" / str(report_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved = []

    for photo in photos:
        filename = photo.filename or f"damage_{uuid.uuid4()}.jpg"
        safe_name = f"{uuid.uuid4()}_{Path(filename).name}"
        file_path = upload_dir / safe_name
        with file_path.open("wb") as buffer:
            buffer.write(photo.file.read())

        saved.append(DamageReportPhoto(report_id=report_id, file_path=str(file_path)))

    return saved


def build_photo_url(file_path: str) -> str:
    normalized = file_path.replace('\\', '/').strip()
    if '/uploads/' in normalized:
        suffix = normalized.split('/uploads/', 1)[1]
        return f"/uploads/{suffix}"
    if normalized.startswith('uploads/'):
        return f"/{normalized}"
    return f"/uploads/{Path(normalized).name}"


class DamageReportService:
    @staticmethod
    def create_report(
        container_id: Optional[str],
        container_no: Optional[str],
        booking_id: Optional[str],
        damage_type: str,
        severity: str,
        location: Optional[str],
        description: str,
        photos: list[UploadFile],
        db: Session,
        user_id: Optional[uuid.UUID]
    ) -> DamageReport:
        if not photos:
            raise HTTPException(status_code=400, detail="At least one damage photo is required")

        validate_images(photos)

        container, _created = resolve_container(container_id, container_no, booking_id, db, user_id)
        normalized_severity = normalize_severity(severity)
        needs_repair = requires_repair(normalized_severity)

        report = DamageReport(
            container_id=container.id,
            container_no=container.container_no,
            damage_type=damage_type.strip(),
            severity=normalized_severity,
            location=(location or "").strip() or None,
            description=description.strip(),
            needs_repair=needs_repair,
            is_resolved=False,
            reported_by=user_id
        )
        db.add(report)
        db.commit()
        db.refresh(report)

        report_id = uuid.UUID(str(report.id))
        saved_photos = save_damage_photos(report_id, photos)
        for photo in saved_photos:
            db.add(photo)

        report.photo_count = len(saved_photos)  # type: ignore[assignment]

        DamageReportService.refresh_container_repair_state(uuid.UUID(str(report.container_id)), db)

        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def list_reports(db: Session) -> list[DamageReport]:
        return db.query(DamageReport).order_by(DamageReport.reported_at.desc()).all()

    @staticmethod
    def get_report(report_id: uuid.UUID, db: Session) -> DamageReport:
        report = db.query(DamageReport).filter(DamageReport.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Damage report not found")
        return report

    @staticmethod
    def serialize_report(report: DamageReport, db: Session) -> dict:
        photos = db.query(DamageReportPhoto).filter(DamageReportPhoto.report_id == report.id).order_by(DamageReportPhoto.uploaded_at.desc()).all()
        return {
            "id": report.id,
            "container_id": report.container_id,
            "container_no": report.container_no,
            "damage_type": report.damage_type,
            "severity": report.severity,
            "location": report.location,
            "description": report.description,
            "photo_count": report.photo_count,
            "needs_repair": report.needs_repair,
            "is_resolved": report.is_resolved,
            "resolved_notes": report.resolved_notes,
            "resolved_at": report.resolved_at,
            "resolved_by": report.resolved_by,
            "reported_by": report.reported_by,
            "reported_at": report.reported_at,
            "updated_at": report.updated_at,
            "photos": [
                {
                    "id": photo.id,
                    "url": build_photo_url(str(photo.file_path)),
                    "uploaded_at": photo.uploaded_at
                }
                for photo in photos
            ]
        }

    @staticmethod
    def update_report(
        report: DamageReport,
        damage_type: str,
        severity: str,
        location: Optional[str],
        description: str,
        db: Session
    ) -> DamageReport:
        normalized_severity = normalize_severity(severity)
        report.damage_type = damage_type.strip()  # type: ignore[assignment]
        report.severity = normalized_severity  # type: ignore[assignment]
        report.location = (location or '').strip() or None  # type: ignore[assignment]
        report.description = description.strip()  # type: ignore[assignment]
        report.needs_repair = requires_repair(normalized_severity)  # type: ignore[assignment]
        report.updated_at = datetime.utcnow()  # type: ignore[assignment]

        if bool(getattr(report, "is_resolved", False)) and bool(getattr(report, "needs_repair", False)):
            report.is_resolved = False  # type: ignore[assignment]
            report.resolved_notes = None  # type: ignore[assignment]
            report.resolved_at = None  # type: ignore[assignment]
            report.resolved_by = None  # type: ignore[assignment]

        DamageReportService.refresh_container_repair_state(uuid.UUID(str(report.container_id)), db)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def add_photos(report: DamageReport, photos: list[UploadFile], db: Session) -> DamageReport:
        if not photos:
            raise HTTPException(status_code=400, detail="Select at least one photo")

        validate_images(photos)
        report_id = uuid.UUID(str(report.id))
        saved_photos = save_damage_photos(report_id, photos)
        for photo in saved_photos:
            db.add(photo)

        current_count = int(getattr(report, "photo_count", 0) or 0)
        report.photo_count = current_count + len(saved_photos)  # type: ignore[assignment]
        report.updated_at = datetime.utcnow()  # type: ignore[assignment]
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def delete_photo(report: DamageReport, photo_id: uuid.UUID, db: Session) -> DamageReport:
        photo = db.query(DamageReportPhoto).filter(
            DamageReportPhoto.id == photo_id,
            DamageReportPhoto.report_id == report.id
        ).first()
        if not photo:
            raise HTTPException(status_code=404, detail="Damage photo not found")

        total = db.query(DamageReportPhoto).filter(DamageReportPhoto.report_id == report.id).count()
        if total <= 1:
            raise HTTPException(status_code=400, detail="At least one damage photo is required")

        try:
            path = Path(str(photo.file_path))
            if path.exists():
                path.unlink()
        except OSError:
            pass

        db.delete(photo)
        current_count = int(getattr(report, "photo_count", 0) or 0)
        report.photo_count = max(0, current_count - 1)  # type: ignore[assignment]
        report.updated_at = datetime.utcnow()  # type: ignore[assignment]
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def resolve_report(
        report: DamageReport,
        user_id: Optional[uuid.UUID],
        notes: Optional[str],
        db: Session
    ) -> DamageReport:
        report.is_resolved = True  # type: ignore[assignment]
        report.resolved_notes = (notes or '').strip() or None  # type: ignore[assignment]
        report.resolved_at = datetime.utcnow()  # type: ignore[assignment]
        report.resolved_by = user_id  # type: ignore[assignment]
        report.updated_at = datetime.utcnow()  # type: ignore[assignment]

        DamageReportService.refresh_container_repair_state(uuid.UUID(str(report.container_id)), db)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def reopen_report(report: DamageReport, db: Session) -> DamageReport:
        report.is_resolved = False  # type: ignore[assignment]
        report.resolved_notes = None  # type: ignore[assignment]
        report.resolved_at = None  # type: ignore[assignment]
        report.resolved_by = None  # type: ignore[assignment]
        report.updated_at = datetime.utcnow()  # type: ignore[assignment]

        DamageReportService.refresh_container_repair_state(uuid.UUID(str(report.container_id)), db)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def refresh_container_repair_state(container_id: uuid.UUID, db: Session) -> None:
        container = db.query(Container).filter(Container.id == container_id).first()
        if not container:
            return

        has_unresolved_blocking = db.query(DamageReport).filter(
            DamageReport.container_id == container_id,
            DamageReport.needs_repair.is_(True),
            DamageReport.is_resolved.is_(False)
        ).count() > 0

        container.needs_repair = bool(has_unresolved_blocking)  # type: ignore
        if has_unresolved_blocking:
            latest = db.query(DamageReport).filter(
                DamageReport.container_id == container_id,
                DamageReport.needs_repair.is_(True),
                DamageReport.is_resolved.is_(False)
            ).order_by(DamageReport.reported_at.desc()).first()
            if latest:
                container.repair_notes = f"Damage Report: {latest.damage_type} - {latest.description}"  # type: ignore
        else:
            container.repair_notes = None  # type: ignore
