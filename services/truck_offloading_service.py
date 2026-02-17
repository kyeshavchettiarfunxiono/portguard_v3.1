"""
Service layer for truck offloading workflows.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.truck_offloading import TruckOffloading, TruckOffloadingStatus, TruckOffloadingStep
from schemas.truck_offloading import TruckOffloadingCreate


class TruckOffloadingService:
    @staticmethod
    def create_truck_offloading(data: TruckOffloadingCreate, db: Session, user_id: Optional[UUID]) -> TruckOffloading:
        truck = TruckOffloading(
            **data.model_dump(),
            status=TruckOffloadingStatus.REGISTERED,
            current_step=TruckOffloadingStep.ARRIVAL_PHOTOS,
            created_by=user_id,
            modified_by=user_id
        )
        db.add(truck)
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def list_trucks(db: Session, status: Optional[TruckOffloadingStatus] = None) -> List[TruckOffloading]:
        query = db.query(TruckOffloading)
        if status:
            query = query.filter(TruckOffloading.status == status)
        return query.order_by(TruckOffloading.created_at.desc()).all()

    @staticmethod
    def get_truck(truck_id: UUID, db: Session) -> TruckOffloading:
        truck = db.query(TruckOffloading).filter(TruckOffloading.id == truck_id).first()
        if not truck:
            raise HTTPException(status_code=404, detail="Truck offloading record not found")
        return truck

    @staticmethod
    def start_offloading(truck: TruckOffloading, user_id: Optional[UUID], db: Session) -> TruckOffloading:
        truck.status = TruckOffloadingStatus.IN_PROGRESS
        truck.current_step = TruckOffloadingStep.ARRIVAL_PHOTOS
        truck.modified_by = user_id
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def record_photo(truck: TruckOffloading, step: TruckOffloadingStep, db: Session) -> TruckOffloading:
        if step == TruckOffloadingStep.ARRIVAL_PHOTOS:
            truck.arrival_photos = (truck.arrival_photos or 0) + 1
        elif step == TruckOffloadingStep.DAMAGE_ASSESSMENT:
            truck.damage_photos = (truck.damage_photos or 0) + 1
        elif step == TruckOffloadingStep.OFFLOADING_PHOTOS:
            truck.offloading_photos = (truck.offloading_photos or 0) + 1
        elif step == TruckOffloadingStep.COMPLETION_PHOTOS:
            truck.completion_photos = (truck.completion_photos or 0) + 1
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def can_advance(truck: TruckOffloading) -> bool:
        if truck.current_step == TruckOffloadingStep.ARRIVAL_PHOTOS:
            return (truck.arrival_photos or 0) >= 2
        if truck.current_step == TruckOffloadingStep.DAMAGE_ASSESSMENT:
            return bool(truck.damage_assessment_completed)
        if truck.current_step == TruckOffloadingStep.OFFLOADING_PHOTOS:
            return (truck.offloading_photos or 0) >= 2
        if truck.current_step == TruckOffloadingStep.COMPLETION_PHOTOS:
            return (truck.completion_photos or 0) >= 2
        if truck.current_step == TruckOffloadingStep.DRIVER_SIGNOFF:
            return bool(truck.signoff_name)
        return False

    @staticmethod
    def advance_step(truck: TruckOffloading, db: Session) -> TruckOffloading:
        if not TruckOffloadingService.can_advance(truck):
            raise HTTPException(status_code=400, detail="Current step is not complete")

        steps = [
            TruckOffloadingStep.ARRIVAL_PHOTOS,
            TruckOffloadingStep.DAMAGE_ASSESSMENT,
            TruckOffloadingStep.OFFLOADING_PHOTOS,
            TruckOffloadingStep.COMPLETION_PHOTOS,
            TruckOffloadingStep.DRIVER_SIGNOFF
        ]
        current_index = steps.index(truck.current_step)
        if current_index < len(steps) - 1:
            truck.current_step = steps[current_index + 1]
            db.commit()
            db.refresh(truck)
        return truck

    @staticmethod
    def revert_step(truck: TruckOffloading, db: Session) -> TruckOffloading:
        steps = [
            TruckOffloadingStep.ARRIVAL_PHOTOS,
            TruckOffloadingStep.DAMAGE_ASSESSMENT,
            TruckOffloadingStep.OFFLOADING_PHOTOS,
            TruckOffloadingStep.COMPLETION_PHOTOS,
            TruckOffloadingStep.DRIVER_SIGNOFF
        ]
        current_index = steps.index(truck.current_step)
        if current_index == 0:
            raise HTTPException(status_code=400, detail="Already at first step")
        truck.current_step = steps[current_index - 1]
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def report_damage(
        truck: TruckOffloading,
        damage_type: str,
        severity: str,
        location: str,
        description: str,
        db: Session
    ) -> TruckOffloading:
        truck.damage_reported = True
        truck.damage_type = damage_type
        truck.damage_severity = severity
        truck.damage_location = location
        truck.damage_description = description
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def complete_damage_assessment(
        truck: TruckOffloading,
        driver_name: str,
        driver_comments: Optional[str],
        db: Session
    ) -> TruckOffloading:
        truck.damage_signoff_name = driver_name
        truck.damage_signoff_comments = driver_comments
        truck.damage_signoff_at = datetime.utcnow()
        truck.damage_assessment_completed = True
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def sign_off(
        truck: TruckOffloading,
        name: str,
        actual_quantity: Optional[float],
        variance_notes: Optional[str],
        db: Session
    ) -> TruckOffloading:
        truck.signoff_name = name
        truck.signoff_at = datetime.utcnow()
        truck.actual_quantity = actual_quantity
        truck.variance_notes = variance_notes
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def complete(truck: TruckOffloading, user_id: Optional[UUID], db: Session) -> TruckOffloading:
        if truck.current_step != TruckOffloadingStep.DRIVER_SIGNOFF:
            raise HTTPException(status_code=400, detail="Complete only after driver sign-off")
        truck.status = TruckOffloadingStatus.COMPLETED
        truck.modified_by = user_id
        db.commit()
        db.refresh(truck)
        return truck
