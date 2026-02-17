import json
import logging
from datetime import datetime
from typing import List, Optional, cast

from sqlalchemy.orm import Session

from models.transnet import (
    TransnetBookingQueue,
    TransnetIngestRow,
    TransnetIngestRun,
    TransnetVesselStack,
)
from services.transnet_scraper import scrape_transnet_schedule

log = logging.getLogger(__name__)


def upsert_transnet_rows(rows: List[dict], db: Session) -> dict:
    updates = 0
    inserts = 0

    for row in rows:
        existing = db.query(TransnetVesselStack).filter(
            TransnetVesselStack.row_hash == row["row_hash"]
        ).first()

        if existing:
            existing.etd = row.get("etd")  # type: ignore[assignment]
            existing.stack_open = row.get("stack_open")  # type: ignore[assignment]
            existing.stack_close = row.get("stack_close")  # type: ignore[assignment]
            existing.berth = row.get("berth")  # type: ignore[assignment]
            existing.status = row.get("status")  # type: ignore[assignment]
            existing.pdf_source_url = row.get("pdf_source_url")  # type: ignore[assignment]
            existing.last_updated = datetime.utcnow()  # type: ignore[assignment]
            updates += 1
        else:
            new_obj = TransnetVesselStack(**row)
            new_obj.last_updated = datetime.utcnow()  # type: ignore[assignment]
            db.add(new_obj)
            inserts += 1

    db.commit()

    return {
        "inserted": inserts,
        "updated": updates,
    }


def create_ingest_run(db: Session, source_url: Optional[str], run_type: str) -> TransnetIngestRun:
    run = TransnetIngestRun(
        run_type=run_type,
        source_url=source_url,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def finalize_ingest_run(
    db: Session,
    run: TransnetIngestRun,
    status: str,
    total_rows: int,
    inserted: int,
    updated: int,
    error_message: Optional[str] = None,
) -> None:
    run.status = status  # type: ignore[assignment]
    run.total_rows = total_rows  # type: ignore[assignment]
    run.inserted = inserted  # type: ignore[assignment]
    run.updated = updated  # type: ignore[assignment]
    run.error_message = error_message  # type: ignore[assignment]
    run.finished_at = datetime.utcnow()  # type: ignore[assignment]
    db.commit()


def store_ingest_rows(db: Session, run_id: int, rows: List[dict]) -> None:
    for row in rows:
        payload = json.dumps(row, default=str)
        db.add(
            TransnetIngestRow(
                run_id=run_id,
                row_hash=row.get("row_hash"),
                payload=payload,
            )
        )
    db.commit()


def sync_booking_queue(db: Session, run_id: int, rows: List[dict]) -> dict:
    inserted = 0
    updated = 0

    for row in rows:
        row_hash = row.get("row_hash")
        if not row_hash:
            continue

        existing = db.query(TransnetBookingQueue).filter(
            TransnetBookingQueue.row_hash == row_hash
        ).first()

        if existing:
            if str(existing.status) == "pending":
                existing.vessel_name = row.get("vessel_name") or existing.vessel_name  # type: ignore[assignment]
                existing.voyage_number = row.get("voyage_number")  # type: ignore[assignment]
                existing.terminal = row.get("terminal")  # type: ignore[assignment]
                existing.berth = row.get("berth")  # type: ignore[assignment]
                existing.eta = row.get("eta")  # type: ignore[assignment]
                existing.pdf_source_url = row.get("pdf_source_url")  # type: ignore[assignment]
                updated += 1
            continue

        db.add(
            TransnetBookingQueue(
                vessel_name=row.get("vessel_name") or "Unknown Vessel",
                voyage_number=row.get("voyage_number"),
                terminal=row.get("terminal"),
                berth=row.get("berth"),
                eta=row.get("eta"),
                status="pending",
                row_hash=row_hash,
                source_run_id=run_id,
                pdf_source_url=row.get("pdf_source_url"),
            )
        )
        inserted += 1

    db.commit()

    return {"inserted": inserted, "updated": updated}


def get_latest_ingest_run(db: Session) -> Optional[TransnetIngestRun]:
    return (
        db.query(TransnetIngestRun)
        .order_by(TransnetIngestRun.started_at.desc())
        .first()
    )


def run_transnet_ingest(
    db: Session,
    source_url: str,
    run_type: str = "manual",
) -> dict:
    run = create_ingest_run(db, source_url, run_type)
    try:
        rows = scrape_transnet_schedule(source_url)

        if rows:
            store_ingest_rows(db, cast(int, run.id), rows)
            result = upsert_transnet_rows(rows, db)
            sync_booking_queue(db, cast(int, run.id), rows)
            status = "success"
        else:
            result = {"inserted": 0, "updated": 0}
            status = "warning"

        finalize_ingest_run(
            db,
            run,
            status,
            total_rows=len(rows),
            inserted=result["inserted"],
            updated=result["updated"],
        )

        return {
            "status": status,
            "inserted": result["inserted"],
            "updated": result["updated"],
            "total": len(rows),
            "run_id": run.id,
        }
    except Exception as exc:
        log.error("Transnet ingest failed: %s", exc, exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        finalize_ingest_run(
            db,
            run,
            status="failed",
            total_rows=0,
            inserted=0,
            updated=0,
            error_message=str(exc),
        )
        return {
            "status": "failed",
            "inserted": 0,
            "updated": 0,
            "total": 0,
            "run_id": run.id,
            "error": str(exc),
        }
