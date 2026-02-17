"""
Service layer for backload truck packing workflows.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.backload_truck import (
    BackloadTruck,
    BackloadTruckStatus,
    BackloadTruckStep,
    BackloadCargoItem
)
from schemas.backload_truck import (
    BackloadTruckCreate,
    BackloadCargoItemCreate,
    BackloadManifestUpdate
)


class BackloadTruckService:
    @staticmethod
    def create_truck(data: BackloadTruckCreate, db: Session, user_id: Optional[UUID]) -> BackloadTruck:
        truck = BackloadTruck(
            **data.model_dump(),
            status=BackloadTruckStatus.REGISTERED,
            current_step=BackloadTruckStep.BEFORE_PHOTOS,
            created_by=user_id,
            modified_by=user_id
        )
        db.add(truck)
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def list_trucks(db: Session, status: Optional[BackloadTruckStatus] = None) -> List[BackloadTruck]:
        query = db.query(BackloadTruck)
        if status:
            query = query.filter(BackloadTruck.status == status)
        return query.order_by(BackloadTruck.created_at.desc()).all()

    @staticmethod
    def get_truck(truck_id: UUID, db: Session) -> BackloadTruck:
        truck = db.query(BackloadTruck).filter(BackloadTruck.id == truck_id).first()
        if not truck:
            raise HTTPException(status_code=404, detail="Backload truck not found")
        return truck

    @staticmethod
    def start_packing(truck: BackloadTruck, user_id: Optional[UUID], db: Session) -> BackloadTruck:
        truck.status = BackloadTruckStatus.IN_PROGRESS
        truck.current_step = BackloadTruckStep.BEFORE_PHOTOS
        truck.modified_by = user_id
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def add_manifest_item(truck: BackloadTruck, data: BackloadCargoItemCreate, db: Session) -> BackloadCargoItem:
        item = BackloadCargoItem(
            truck_id=truck.id,
            description=data.description,
            quantity=data.quantity,
            unit=data.unit,
            weight_kg=data.weight_kg
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_manifest(truck: BackloadTruck, data: BackloadManifestUpdate, db: Session) -> BackloadTruck:
        truck.total_cargo_weight = data.total_cargo_weight
        truck.transfer_order_number = data.transfer_order_number
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def record_photo(truck: BackloadTruck, step: BackloadTruckStep, db: Session) -> BackloadTruck:
        if step == BackloadTruckStep.BEFORE_PHOTOS:
            truck.before_photos = (truck.before_photos or 0) + 1
        elif step == BackloadTruckStep.PACKING_PHOTOS:
            truck.packing_photos = (truck.packing_photos or 0) + 1
        elif step == BackloadTruckStep.AFTER_PHOTOS:
            truck.after_photos = (truck.after_photos or 0) + 1
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def can_advance(truck: BackloadTruck, db: Session) -> bool:
        if truck.current_step == BackloadTruckStep.BEFORE_PHOTOS:
            return (truck.before_photos or 0) >= 2
        if truck.current_step == BackloadTruckStep.MANIFEST_WEIGHTS:
            item_count = db.query(BackloadCargoItem).filter(BackloadCargoItem.truck_id == truck.id).count()
            return item_count > 0 and bool(truck.total_cargo_weight)
        if truck.current_step == BackloadTruckStep.PACKING_PHOTOS:
            return (truck.packing_photos or 0) >= 2
        if truck.current_step == BackloadTruckStep.AFTER_PHOTOS:
            return (truck.after_photos or 0) >= 2
        if truck.current_step == BackloadTruckStep.DRIVER_SIGNOFF:
            return bool(truck.signoff_name)
        return False

    @staticmethod
    def advance_step(truck: BackloadTruck, db: Session) -> BackloadTruck:
        if not BackloadTruckService.can_advance(truck, db):
            raise HTTPException(status_code=400, detail="Current step is not complete")

        steps = [
            BackloadTruckStep.BEFORE_PHOTOS,
            BackloadTruckStep.MANIFEST_WEIGHTS,
            BackloadTruckStep.PACKING_PHOTOS,
            BackloadTruckStep.AFTER_PHOTOS,
            BackloadTruckStep.DRIVER_SIGNOFF
        ]
        current_index = steps.index(truck.current_step)
        if current_index < len(steps) - 1:
            truck.current_step = steps[current_index + 1]
            db.commit()
            db.refresh(truck)
        return truck

    @staticmethod
    def revert_step(truck: BackloadTruck, db: Session) -> BackloadTruck:
        steps = [
            BackloadTruckStep.BEFORE_PHOTOS,
            BackloadTruckStep.MANIFEST_WEIGHTS,
            BackloadTruckStep.PACKING_PHOTOS,
            BackloadTruckStep.AFTER_PHOTOS,
            BackloadTruckStep.DRIVER_SIGNOFF
        ]
        current_index = steps.index(truck.current_step)
        if current_index == 0:
            raise HTTPException(status_code=400, detail="Already at first step")
        truck.current_step = steps[current_index - 1]
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def sign_off(truck: BackloadTruck, name: str, db: Session) -> BackloadTruck:
        truck.signoff_name = name
        truck.signoff_at = datetime.utcnow()
        db.commit()
        db.refresh(truck)
        return truck

    @staticmethod
    def complete(truck: BackloadTruck, user_id: Optional[UUID], db: Session) -> BackloadTruck:
        if truck.current_step != BackloadTruckStep.DRIVER_SIGNOFF:
            raise HTTPException(status_code=400, detail="Complete only after driver sign-off")
        truck.status = BackloadTruckStatus.COMPLETED
        truck.modified_by = user_id
        db.commit()
        db.refresh(truck)
        return truck
