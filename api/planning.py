from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.dependencies import require_admin, require_management
from core.database import get_db
from models.booking import Booking
from models.plan import Plan, PlanStatus
from models.user import User
from schemas.plan import PlanCreate, PlanResponse, PlanUpdate

router = APIRouter(prefix="/plans", tags=["planning"])


def _serialize_plan(plan: Plan) -> dict:
    status_value = plan.status.value if hasattr(plan.status, "value") else str(plan.status)
    return {
        "id": plan.id,
        "booking_id": plan.booking_id,
        "vessel_name": plan.vessel_name,
        "planned_quantity": plan.planned_quantity,
        "planned_date": plan.planned_date,
        "status": status_value,
        "created_at": plan.created_at,
        "created_by": plan.created_by,
    }


@router.get("/", response_model=List[PlanResponse])
def list_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    plans = db.query(Plan).order_by(Plan.planned_date.asc()).all()
    return [_serialize_plan(plan) for plan in plans]


@router.post("/", response_model=PlanResponse)
def create_plan(
    payload: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    plan = Plan(
        booking_id=payload.booking_id,
        vessel_name=booking.vessel_name,
        planned_quantity=payload.planned_quantity,
        planned_date=payload.planned_date,
        status=PlanStatus.DRAFT,
        created_by=current_user.id,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return _serialize_plan(plan)


@router.put("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: UUID,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    current_status = plan.status.value if hasattr(plan.status, "value") else str(plan.status)
    if current_status not in {PlanStatus.DRAFT.value, PlanStatus.LOCKED.value}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT/LOCKED plans can be updated",
        )

    if payload.planned_quantity is not None:
        setattr(plan, "planned_quantity", payload.planned_quantity)
    if payload.planned_date is not None:
        setattr(plan, "planned_date", payload.planned_date)
    if payload.status is not None:
        normalized_status = payload.status.strip().upper()
        allowed_status = {item.value for item in PlanStatus}
        if normalized_status not in allowed_status:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")
        setattr(plan, "status", normalized_status)

    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


@router.post("/{plan_id}/finalize")
def finalize_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    current_status = plan.status.value if hasattr(plan.status, "value") else str(plan.status)
    if current_status != PlanStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT plans can be finalized",
        )

    setattr(plan, "status", PlanStatus.LOCKED.value)
    db.commit()
    db.refresh(plan)
    return {"status": "LOCKED", "message": "Truck plan finalized", "plan": _serialize_plan(plan)}


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    current_status = plan.status.value if hasattr(plan.status, "value") else str(plan.status)
    if current_status != PlanStatus.DRAFT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DRAFT plans can be deleted",
        )

    db.delete(plan)
    db.commit()
    return {"message": "Plan deleted successfully"}
