# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.plan import Plan, PlanStatus
from schemas.plan import PlanCreate, PlanUpdate, PlanResponse

router = APIRouter(prefix="/plans", tags=["planning"])


@router.post("/", response_model=PlanResponse)
def create_plan(
    plan: PlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new plan in DRAFT status."""
    new_plan = Plan(
        plan_name=plan.plan_name,
        plan_type=plan.plan_type,
        status=PlanStatus.DRAFT,
        created_by=current_user.id
    )
    db.add(new_plan)
    db.commit()
    db.refresh(new_plan)
    return new_plan


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db)
):
    """Retrieve a plan by ID."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Plan UUID format")
    
    plan = db.query(Plan).filter(Plan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


@router.put("/{plan_id}", response_model=PlanResponse)
def update_plan(
    plan_id: str,
    plan_update: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a plan (only in DRAFT status)."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Plan UUID format")
    
    plan = db.query(Plan).filter(Plan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan_status = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
    if plan_status != PlanStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Can only edit plans in DRAFT status"
        )
    
    if plan_update.plan_name:
        plan.plan_name = plan_update.plan_name
    
    plan.modified_by = current_user.id
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}")
def delete_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a plan (only in DRAFT status)."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Plan UUID format")
    
    plan = db.query(Plan).filter(Plan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan_status = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
    if plan_status != PlanStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Can only delete plans in DRAFT status"
        )
    
    db.delete(plan)
    db.commit()
    return {"message": "Plan deleted successfully"}


@router.post("/{plan_id}/finalize")
def finalize_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lock plan for execution (DRAFT → LOCKED)."""
    try:
        plan_uuid = UUID(plan_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Plan UUID format")
    
    plan = db.query(Plan).filter(Plan.id == plan_uuid).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan_status = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
    if plan_status != PlanStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Can only finalize plans in DRAFT status"
        )
    
    plan.status = PlanStatus.LOCKED.value  # type: ignore
    plan.is_locked = True
    plan.modified_by = current_user.id
    db.commit()
    return {"status": "LOCKED", "message": "Plan finalized"}