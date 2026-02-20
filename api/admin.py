"""
Admin endpoints for user management and system overview.
"""
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.dependencies import require_admin
from core.database import get_db
from models.booking import Booking
from models.container import Container, ContainerStatus
from models.downtime import Downtime
from models.user import User
from schemas.user import UserCreate, UserResponse
from services.auth_service import AuthService
from services.config_service import get_downtime_hourly_rate, set_downtime_hourly_rate

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
ALLOWED_ROLES = {"OPERATOR", "SUPERVISOR", "MANAGER", "ADMIN", "SUPERUSER"}


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


class DowntimeRateUpdate(BaseModel):
    hourly_rate: float = Field(..., gt=0)


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    """List all users for admin management."""
    return db.query(User).order_by(User.username).all()


@router.post("/users", response_model=UserResponse)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new staff user."""
    requested_role = str(payload.role).strip().upper()
    if requested_role not in ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    if requested_role == "SUPERUSER" and str(current_user.role) != "SUPERUSER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPERUSER can create SUPERUSER accounts")

    payload.role = requested_role
    return AuthService.register_user(payload, db)


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update an existing user (role/active state)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_role = str(current_user.role)
    target_role = str(user.role)

    if target_role == "SUPERUSER" and current_role != "SUPERUSER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPERUSER can manage SUPERUSER accounts")

    if payload.role is not None:
        normalized_role = str(payload.role).strip().upper()
        if normalized_role not in ALLOWED_ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
        if normalized_role == "SUPERUSER" and current_role != "SUPERUSER":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPERUSER can assign SUPERUSER role")
        user.role = normalized_role  # type: ignore[assignment]
    if payload.is_active is not None:
        if str(user.id) == str(current_user.id) and payload.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")
        user.is_active = payload.is_active  # type: ignore[assignment]

    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Deactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if str(user.id) == str(current_user.id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")

    if str(user.role) == "SUPERUSER" and str(current_user.role) != "SUPERUSER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPERUSER can deactivate SUPERUSER accounts")

    user.is_active = False  # type: ignore[assignment]
    db.commit()
    db.refresh(user)
    return user


@router.get("/config/downtime-rate")
def get_downtime_rate():
    """Return the current downtime hourly rate (ZAR)."""
    return {"hourly_rate": get_downtime_hourly_rate()}


@router.post("/config/downtime-rate")
def update_downtime_rate(payload: DowntimeRateUpdate):
    """Update the downtime hourly rate (ZAR)."""
    set_downtime_hourly_rate(payload.hourly_rate)
    return {"hourly_rate": get_downtime_hourly_rate()}


@router.get("/overview")
def get_admin_overview(
    db: Session = Depends(get_db),
    timeframe: Optional[str] = Query(default=None, pattern="^(today|week|month)$")
):
    """Return system overview for the admin dashboard."""
    active_jobs = db.query(Container).filter(
        Container.status.in_([ContainerStatus.PACKING, ContainerStatus.UNPACKING])  # type: ignore
    ).count()

    now = datetime.utcnow()
    downtime_query = db.query(Downtime)
    filter_start: Optional[datetime] = None
    if timeframe == "today":
        filter_start = datetime(now.year, now.month, now.day)
    elif timeframe == "week":
        filter_start = now - timedelta(days=7)
    elif timeframe == "month":
        filter_start = now - timedelta(days=30)

    if filter_start is not None:
        downtime_query = downtime_query.filter(Downtime.start_time >= filter_start)

    downtimes = downtime_query.all()
    hourly_rate = get_downtime_hourly_rate()
    total_cost = 0.0

    for dt in downtimes:
        if dt.end_time is None:
            duration_hours = (now - dt.start_time).total_seconds() / 3600
        else:
            duration_hours = (dt.end_time - dt.start_time).total_seconds() / 3600
        total_cost += duration_hours * hourly_rate

    revenue_by_vessel = []
    revenue_query = (
        db.query(
            Booking.vessel_name.label("vessel_name"),
            func.sum(
                func.extract(
                    "epoch",
                    func.coalesce(Downtime.end_time, func.now()) - Downtime.start_time
                )
            ).label("total_seconds")
        )
        .join(Container, Container.booking_id == Booking.id)
        .join(Downtime, Downtime.container_id == Container.id)
        .group_by(Booking.vessel_name)
    )
    if filter_start is not None:
        revenue_query = revenue_query.filter(Downtime.start_time >= filter_start)

    try:
        revenue_rows = revenue_query.all()
        for row in revenue_rows:
            total_seconds = row.total_seconds or 0
            revenue_by_vessel.append(
                {
                    "vessel_name": row.vessel_name,
                    "revenue_impact_zar": round((total_seconds / 3600) * hourly_rate, 2)
                }
            )
    except Exception:
        fallback_query = (
            db.query(Booking.vessel_name, Downtime.start_time, Downtime.end_time)
            .join(Container, Container.booking_id == Booking.id)
            .join(Downtime, Downtime.container_id == Container.id)
        )
        if filter_start is not None:
            fallback_query = fallback_query.filter(Downtime.start_time >= filter_start)

        totals: dict[str, float] = {}
        for vessel_name, start_time, end_time in fallback_query.all():
            effective_end = end_time or now
            duration_hours = (effective_end - start_time).total_seconds() / 3600
            totals[vessel_name] = totals.get(vessel_name, 0.0) + duration_hours

        for vessel_name, hours in totals.items():
            revenue_by_vessel.append(
                {
                    "vessel_name": vessel_name,
                    "revenue_impact_zar": round(hours * hourly_rate, 2)
                }
            )

    revenue_by_vessel.sort(key=lambda item: item["revenue_impact_zar"], reverse=True)

    return {
        "active_jobs": active_jobs,
        "total_downtime_cost_zar": round(total_cost, 2),
        "hourly_rate": hourly_rate,
        "revenue_by_vessel": revenue_by_vessel
    }
