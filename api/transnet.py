from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.security import get_current_user
from models.transnet import TransnetBookingQueue, TransnetVesselStack
from services.transnet_service import get_latest_ingest_run, run_transnet_ingest

router = APIRouter(prefix="/api/transnet", tags=["transnet"])


class BookingApprovalPayload(BaseModel):
    booking_id: UUID


@router.get("/vessels")
def list_vessels(
    q: Optional[str] = Query(None, description="Search vessel or voyage"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    query = db.query(TransnetVesselStack)
    if q:
        like = f"%{q.strip().lower()}%"
        query = query.filter(
            (TransnetVesselStack.vessel_name.ilike(like))
            | (TransnetVesselStack.voyage_number.ilike(like))
        )
    vessels = query.order_by(TransnetVesselStack.eta.asc().nulls_last()).limit(200).all()
    return [
        {
            "id": v.id,
            "vessel_name": v.vessel_name,
            "voyage_number": v.voyage_number,
            "terminal": v.terminal,
            "berth": v.berth,
            "eta": v.eta,
            "etd": v.etd,
            "stack_open": v.stack_open,
            "stack_close": v.stack_close,
            "status": v.status,
            "pdf_source_url": v.pdf_source_url,
            "last_updated": v.last_updated,
        }
        for v in vessels
    ]


@router.get("/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    total = db.query(TransnetVesselStack).count()
    open_stacks = db.query(TransnetVesselStack).filter(
        TransnetVesselStack.stack_open.isnot(None)
    ).count()
    closed_stacks = db.query(TransnetVesselStack).filter(
        TransnetVesselStack.stack_close.isnot(None)
    ).count()
    latest_run = get_latest_ingest_run(db)

    return {
        "total_vessels": total,
        "stacks_open": open_stacks,
        "stacks_closed": closed_stacks,
        "generated_at": datetime.utcnow(),
        "last_ingest_at": latest_run.finished_at if latest_run else None,
        "last_ingest_status": latest_run.status if latest_run else None,
    }


@router.get("/dashboard/ingest")
def latest_ingest(
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    run = get_latest_ingest_run(db)
    if not run:
        return {"status": "empty"}
    return {
        "status": run.status,
        "run_id": run.id,
        "run_type": run.run_type,
        "source_url": run.source_url,
        "total_rows": run.total_rows,
        "inserted": run.inserted,
        "updated": run.updated,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "error_message": run.error_message,
    }


@router.post("/live-scrape")
def live_scrape(
    terminal_url: str = Query(
        "https://www.transnetportterminals.net/Ports/Pages/Terminal%20Updates.aspx",
        description="TPT Page URL containing the stack list",
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in {"SUPERVISOR", "MANAGER", "ADMIN", "SUPERUSER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    result = run_transnet_ingest(db, terminal_url, run_type="manual")

    if result["status"] == "failed":
        return {
            "status": "error",
            "message": "Scraper failed. Check logs for details.",
            "inserted": 0,
            "updated": 0,
        }

    if result["status"] == "warning":
        return {
            "status": "warning",
            "message": "Scraper ran but found no vessels.",
            "inserted": 0,
            "updated": 0,
        }

    return {
        "status": "success",
        "message": f"Scrape complete. {result['inserted']} new, {result['updated']} updated.",
        "inserted": result["inserted"],
        "updated": result["updated"],
    }


@router.get("/booking-queue")
def list_booking_queue(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in {"SUPERVISOR", "MANAGER", "ADMIN", "SUPERUSER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    query = db.query(TransnetBookingQueue)
    if status_filter:
        query = query.filter(TransnetBookingQueue.status == status_filter)
    items = query.order_by(TransnetBookingQueue.created_at.desc()).all()

    return [
        {
            "id": item.id,
            "vessel_name": item.vessel_name,
            "voyage_number": item.voyage_number,
            "terminal": item.terminal,
            "berth": item.berth,
            "eta": item.eta,
            "status": item.status,
            "row_hash": item.row_hash,
            "pdf_source_url": item.pdf_source_url,
            "booking_id": item.booking_id,
            "approved_at": item.approved_at,
            "declined_at": item.declined_at,
        }
        for item in items
    ]


@router.post("/booking-queue/{queue_id}/approve")
def approve_booking_queue(
    queue_id: int,
    payload: BookingApprovalPayload,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in {"SUPERVISOR", "MANAGER", "ADMIN", "SUPERUSER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    item = db.query(TransnetBookingQueue).filter(TransnetBookingQueue.id == queue_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if str(item.status) != "pending":
        raise HTTPException(status_code=409, detail="Queue item is not pending")

    item.status = "approved"  # type: ignore[assignment]
    item.booking_id = payload.booking_id  # type: ignore[assignment]
    item.approved_by = current_user.id  # type: ignore[assignment]
    item.approved_at = datetime.utcnow()  # type: ignore[assignment]
    db.commit()

    return {"status": "approved", "id": item.id}


@router.post("/booking-queue/{queue_id}/decline")
def decline_booking_queue(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in {"SUPERVISOR", "MANAGER", "ADMIN", "SUPERUSER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    item = db.query(TransnetBookingQueue).filter(TransnetBookingQueue.id == queue_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if str(item.status) != "pending":
        raise HTTPException(status_code=409, detail="Queue item is not pending")

    item.status = "declined"  # type: ignore[assignment]
    item.declined_by = current_user.id  # type: ignore[assignment]
    item.declined_at = datetime.utcnow()  # type: ignore[assignment]
    db.commit()

    return {"status": "declined", "id": item.id}


@router.post("/booking-queue/{queue_id}/requeue")
def requeue_booking_queue(
    queue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in {"SUPERVISOR", "MANAGER", "ADMIN", "SUPERUSER"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    item = db.query(TransnetBookingQueue).filter(TransnetBookingQueue.id == queue_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if str(item.status) != "declined":
        raise HTTPException(status_code=409, detail="Queue item is not declined")

    item.status = "pending"  # type: ignore[assignment]
    item.declined_by = None  # type: ignore[assignment]
    item.declined_at = None  # type: ignore[assignment]
    db.commit()

    return {"status": "pending", "id": item.id}
