# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Union, cast as py_cast
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from models.container import Container, ContainerStatus, ContainerType
from models.evidence import ContainerImage
from models.downtime import Downtime, DowntimeType
from schemas.container import ContainerCreate
from services.config_service import get_downtime_hourly_rate

try:
    from models.booking import Booking
except ImportError:
    Booking = None


class ContainerService:
    """Service layer for container operations."""
    
    @staticmethod
    def create_container(
        container_data: ContainerCreate,
        user_id: Optional[uuid.UUID],
        db: Session
    ) -> Container:
        """Register a new container with validation."""
        # DEBUG LOGGING
        print(f"DEBUG: create_container called")
        print(f"DEBUG: Payload: {container_data.model_dump()}")
        print(f"DEBUG: User ID: {user_id}")

        db_container = db.query(Container).filter(
            Container.container_no == container_data.container_no
        ).first()
        
        if db_container:
            raise HTTPException(
                status_code=400,
                detail="Container already registered."
            )
        
        # Convert Pydantic model to dict and create Container instance
        data = container_data.model_dump()
        new_container = Container(**data)
        if user_id is not None:
            new_container.created_by = user_id  # type: ignore[assignment]
            new_container.modified_by = user_id  # type: ignore[assignment]
        
        # Ensure status is set to REGISTERED (should be default, but explicit is good)
        new_container.status = ContainerStatus.REGISTERED
        
        db.add(new_container)
        db.commit()
        db.refresh(new_container)
        return new_container
    
    @staticmethod
    def get_container(container_id: str, db: Session) -> Container:
        """Fetch container by ID with UUID validation."""
        try:
            container_uuid = uuid.UUID(container_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Container UUID format")
        
        container = db.query(Container).filter(Container.id == container_uuid).first()
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        return container
    
    @staticmethod
    def list_containers(db: Session) -> List[Container]:
        """List all containers with booking relationships loaded."""
        return db.query(Container).options(joinedload(Container.booking)).all()
    
    @staticmethod
    def transition_container_status(
        container_id: str,
        new_status: ContainerStatus,
        user_id: uuid.UUID,
        db: Session
    ) -> Container:
        """Transition container to a new status with validation."""
        container = ContainerService.get_container(container_id, db)
        
        try:
            container.transition_to(new_status, user_id)
            db.commit()
            db.refresh(container)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        return container
    
    @staticmethod
    def finalize_container(
        container_id: str,
        user_id: uuid.UUID,
        db: Session
    ) -> Container:
        """Finalize container after review (PENDING_REVIEW → FINALIZED)."""
        container = ContainerService.get_container(container_id, db)
        
        if py_cast(ContainerStatus, container.status) != ContainerStatus.PENDING_REVIEW:
            raise HTTPException(
                status_code=400,
                detail=f"Container must be in PENDING_REVIEW status. Current: {container.status}"
            )
        
        container.transition_to(ContainerStatus.FINALIZED, user_id)
        container.modified_at = datetime.utcnow()
        db.commit()
        db.refresh(container)
        return container
    
    @staticmethod
    def get_container_evidence(
        container_id: str,
        db: Session
    ) -> dict:
        """Get evidence gallery for a container."""
        container = ContainerService.get_container(container_id, db)
        
        images = db.query(ContainerImage).filter(
            ContainerImage.container_id == container.id
        ).all()
        
        image_gallery = []
        for img in images:
            file_path_str = str(img.file_path)
            file_name = Path(file_path_str).name
            image_gallery.append({
                "type": img.image_type,
                "url": f"http://127.0.0.1:8000/static/{container_id}/{file_name}",
                "uploaded_at": img.uploaded_at
            })
        
        return {
            "container_no": container.container_no,
            "status": container.status,
            "total_images": len(image_gallery),
            "gallery": image_gallery
        }
    
    @staticmethod
    def get_vessel_bookings_with_priority(db: Session) -> List[dict]:
        """Fetch all vessel bookings and calculate priority alerts."""
        if not Booking:
            return []
        
        bookings = db.query(Booking).all()
        result = []
        now = datetime.utcnow()
        
        for booking in bookings:
            time_until_stack = booking.stack_date - now
            is_priority = timedelta(hours=0) <= time_until_stack <= timedelta(hours=24)
            
            result.append({
                "booking_id": str(booking.id),
                "vessel_name": getattr(booking, 'vessel_name', 'N/A'),
                "stack_date": booking.stack_date.isoformat(),
                "hours_until_stack": round(time_until_stack.total_seconds() / 3600, 2),
                "priority_alert": is_priority,
                "urgency_level": "CRITICAL" if is_priority else "NORMAL"
            })
        
        return sorted(result, key=lambda x: x["hours_until_stack"])
    
    @staticmethod
    def resolve_downtime(
        container_id: str,
        downtime_type: str,
        reason: Optional[str],
        start_time: datetime,
        end_time: Optional[datetime],
        user_id: Optional[uuid.UUID],
        db: Session
    ) -> dict:
        """Calculate downtime duration and cost impact."""
        container = ContainerService.get_container(container_id, db)
        
        try:
            dt_type = DowntimeType[downtime_type.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid downtime type. Use: {[t.value for t in DowntimeType]}"
            )
        
        new_downtime = Downtime(
            container_id=container.id,
            downtime_type=dt_type,
            reason=reason,
            start_time=start_time,
            end_time=end_time,
            hourly_rate=get_downtime_hourly_rate(),
            created_by=user_id
        )
        
        cost_calculation = new_downtime.calculate_cost()
        
        db.add(new_downtime)
        db.commit()
        db.refresh(new_downtime)
        
        return {
            "downtime_id": str(new_downtime.id),
            "container_id": container_id,
            "type": downtime_type,
            "reason": reason,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            **cost_calculation
        }
    
    @staticmethod
    def calculate_total_downtime_cost(
        value: Union[str, float],
        db: Optional[Session] = None,
        rate_per_hour: float = 250.0
    ) -> float:
        """
        Calculate downtime cost.

        - If value is a float, it is treated as downtime hours.
        - If value is a container_id string, a DB session is required.
        """
        if isinstance(value, (int, float)):
            return float(value) * float(rate_per_hour)

        if db is None:
            raise HTTPException(status_code=400, detail="DB session required for container cost lookup")

        container_uuid = uuid.UUID(value)
        downtimes = db.query(Downtime).filter(
            Downtime.container_id == container_uuid
        ).all()

        total_cost = 0.0
        for dt in downtimes:
            if dt.cost_impact is None:
                continue
            total_cost += float(dt.cost_impact)  # type: ignore

        return round(total_cost, 2)

    @staticmethod
    def get_container_downtime_summary(
        container_id: str,
        db: Session
    ) -> dict:
        """Get total downtime and cost impact for a container."""
        container = ContainerService.get_container(container_id, db)
        
        downtimes = db.query(Downtime).filter(
            Downtime.container_id == container.id
        ).all()
        
        total_duration = 0.0
        total_cost = 0.0
        downtime_list = []
        
        for dt in downtimes:
            calc = dt.calculate_cost()
            if calc["status"] == "COMPLETED":
                # FIX: Use type: ignore for Column type casting
                dur_val: float = float(dt.duration_hours) if dt.duration_hours is not None else 0.0  # type: ignore
                cost_val: float = float(dt.cost_impact) if dt.cost_impact is not None else 0.0  # type: ignore
                total_duration += dur_val
                total_cost += cost_val
            
            # FIX: Extract values before casting/rounding
            dur_for_display: float = float(dt.duration_hours) if dt.duration_hours is not None else 0.0  # type: ignore
            cost_for_display: float = float(dt.cost_impact) if dt.cost_impact is not None else 0.0  # type: ignore
            
            downtime_list.append({
                "id": str(dt.id),
                "type": dt.downtime_type.value,
                "reason": dt.reason,
                "start": dt.start_time.isoformat(),
                "end": dt.end_time.isoformat() if dt.end_time is not None else None,
                "duration_hours": round(dur_for_display, 2) if dt.duration_hours is not None else None,
                "cost": round(cost_for_display, 2) if dt.cost_impact is not None else None
            })
        
        return {
            "container_id": container_id,
            "total_downtime_hours": round(float(total_duration), 2),
            "total_cost_impact_zar": round(float(total_cost), 2),
            "downtime_events": downtime_list
        }
