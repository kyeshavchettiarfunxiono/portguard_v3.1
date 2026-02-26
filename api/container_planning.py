from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import String, cast as sql_cast, func
from sqlalchemy.orm import Session

from api.dependencies import require_management
from core.database import get_db
from models.booking import Booking
from models.container import Container, ContainerStatus
from models.container_planning_entry import ContainerPlanningEntry
from models.user import User
from schemas.container_planning_entry import (
    BookingOptionResponse,
    ContainerPlanningCreateRequest,
    ContainerPlanningResponse,
    ContainerPlanningSummaryResponse,
)

router = APIRouter(prefix="/container-plans", tags=["container-planning"])


@router.get("/booking-options", response_model=list[BookingOptionResponse])
def list_booking_options(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    bookings = db.query(Booking).order_by(Booking.created_at.desc()).all()
    return [
        BookingOptionResponse(
            id=cast(UUID, booking.id),
            booking_reference=cast(str, booking.booking_reference),
            vessel_name=cast(str, booking.vessel_name),
            client=cast(str, booking.client),
            container_type=cast(str, booking.container_type),
        )
        for booking in bookings
    ]


@router.post("/", response_model=ContainerPlanningResponse)
def create_container_plan(
    payload: ContainerPlanningCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    plan = ContainerPlanningEntry(
        planning_date=payload.planning_date,
        booking_id=payload.booking_id,
        booking_reference=payload.booking_reference,
        vessel_name=payload.vessel_name,
        client_name=payload.client_name,
        container_type=payload.container_type,
        planned_quantity=payload.planned_quantity,
        notes=payload.notes,
        created_by=cast(UUID, current_user.id),
        modified_by=cast(UUID, current_user.id),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return cast(ContainerPlanningResponse, plan)


@router.get("/", response_model=list[ContainerPlanningResponse])
def list_container_plans(
    planning_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    plans = (
        db.query(ContainerPlanningEntry)
        .filter(ContainerPlanningEntry.planning_date == planning_date)
        .order_by(ContainerPlanningEntry.created_at.desc())
        .all()
    )
    return [cast(ContainerPlanningResponse, item) for item in plans]


@router.get("/summary", response_model=ContainerPlanningSummaryResponse)
def get_container_plan_summary(
    planning_date: date = Query(default_factory=date.today),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    planned_total = (
        db.query(func.coalesce(func.sum(ContainerPlanningEntry.planned_quantity), 0))
        .filter(ContainerPlanningEntry.planning_date == planning_date)
        .scalar()
        or 0
    )

    start_dt = datetime.combine(planning_date, datetime.min.time())
    end_dt = start_dt + timedelta(days=1)

    actual_total = (
        db.query(Container)
        .filter(Container.created_at >= start_dt, Container.created_at < end_dt)
        .count()
    )

    completed_total = (
        db.query(Container)
        .filter(
            Container.modified_at >= start_dt,  # type: ignore[arg-type]
            Container.modified_at < end_dt,  # type: ignore[arg-type]
            sql_cast(Container.status, String) == ContainerStatus.FINALIZED.value,
        )
        .count()
    )

    return ContainerPlanningSummaryResponse(
        planning_date=planning_date,
        planned_containers=int(planned_total),
        actual_containers=int(actual_total),
        variance=int(actual_total) - int(planned_total),
        completed_containers=int(completed_total),
    )


@router.delete("/{plan_id}")
def delete_container_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    plan = db.query(ContainerPlanningEntry).filter(ContainerPlanningEntry.id == plan_id).first()
    if not plan:
        return {"deleted": False, "reason": "not_found"}

    db.delete(plan)
    db.commit()
    return {"deleted": True, "plan_id": str(plan_id)}
