"""
Service layer for cargo manifest and damage reporting.
"""
from uuid import UUID
from sqlalchemy.orm import Session
from typing import Optional, List
from models.cargo import CargoItem
from models.container import Container

class CargoService:
    @staticmethod
    def record_cargo_item(
        container_id: str,
        description: str,
        quantity: int,
        unit: str,
        condition: str,
        notes: str,
        inspector_id: UUID,
        db: Session
    ):
        """Record a cargo item in the manifest."""
        cargo_item = CargoItem(
            container_id=UUID(container_id),
            description=description,
            quantity=quantity,
            unit=unit,
            condition=condition,
            notes=notes,
            inspector_id=inspector_id
        )
        db.add(cargo_item)
        db.commit()
        db.refresh(cargo_item)
        
        return {
            "status": "success",
            "cargo_id": str(cargo_item.id),
            "message": "Cargo item recorded",
            "condition": condition
        }

    @staticmethod
    def get_cargo_manifest(container_id: str, db: Session):
        """Get all cargo items for a container."""
        items = db.query(CargoItem).filter(
            CargoItem.container_id == UUID(container_id)
        ).all()
        
        return {
            "container_id": container_id,
            "total_items": len(items),
            "total_quantity": sum(item.quantity for item in items),
            "items": items
        }

    @staticmethod
    def get_damaged_cargo_report(container_id: str, db: Session):
        """Get report of damaged cargo items."""
        damaged_items = db.query(CargoItem).filter(
            CargoItem.container_id == UUID(container_id),
            CargoItem.condition != "GOOD"
        ).all()
        
        return {
            "container_id": container_id,
            "has_issues": len(damaged_items) > 0,
            "problem_items_count": len(damaged_items),
            "items": damaged_items
        }