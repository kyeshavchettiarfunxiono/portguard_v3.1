"""
Cargo manifest service for unpacking operations.
"""
import uuid
from typing import List
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.cargo import CargoItem, CargoCondition
from models.container import Container
from models.unpacking import UnpackingSession


class CargoService:
    """Service for cargo manifest operations."""
    
    @staticmethod
    def record_cargo_item(
        container_id: str,
        description: str,
        quantity: int,
        unit: str,
        condition: str,
        notes: str,
        inspector_id: uuid.UUID,
        db: Session
    ) -> dict:
        """Record unpacked cargo item in manifest."""
        try:
            container_uuid = uuid.UUID(container_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Container UUID format")
        
        container = db.query(Container).filter(Container.id == container_uuid).first()
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        try:
            cargo_condition = CargoCondition[condition.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid condition. Use: {[c.value for c in CargoCondition]}"
            )
        
        new_item = CargoItem(
            container_id=container_uuid,
            description=description,
            quantity=quantity,
            unit=unit,
            condition=cargo_condition,
            notes=notes,
            recorded_by=inspector_id
        )
        
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        
        return {
            "cargo_id": str(new_item.id),
            "container_id": container_id,
            "description": new_item.description,
            "quantity": new_item.quantity,
            "unit": new_item.unit,
            "condition": new_item.condition.value,
            "notes": new_item.notes,
            "recorded_by": str(new_item.recorded_by),
            "recorded_at": new_item.created_at.isoformat()
        }
    
    @staticmethod
    def get_cargo_manifest(container_id: str, db: Session) -> dict:
        """Retrieve full cargo manifest for a container."""
        try:
            container_uuid = uuid.UUID(container_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Container UUID format")
        
        container = db.query(Container).filter(Container.id == container_uuid).first()
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        items = db.query(CargoItem).filter(
            CargoItem.container_id == container_uuid
        ).order_by(CargoItem.created_at).all()
        unpacking_session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_uuid
        ).first()
        manifest_documented_at = (
            unpacking_session.manifest_documented_at if unpacking_session is not None else None
        )
        
        manifest = []
        total_quantity = 0
        
        for item in items:
            total_quantity += item.quantity
            
            manifest.append({
                "cargo_id": str(item.id),
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "condition": item.condition.value,
                "notes": item.notes,
                "recorded_by_id": str(item.recorded_by),
                "recorded_at": item.created_at.isoformat()
            })
        
        return {
            "container_id": container_id,
            "container_no": container.container_no,
            "manifest_vessel_name": container.manifest_vessel_name,
            "manifest_voyage_number": container.manifest_voyage_number,
            "depot_list_fcl_count": container.depot_list_fcl_count,
            "depot_list_grp_count": container.depot_list_grp_count,
            "manifest_document_reference": unpacking_session.manifest_document_reference if unpacking_session else None,
            "manifest_notes": unpacking_session.manifest_notes if unpacking_session else None,
            "manifest_documented_at": manifest_documented_at.isoformat() if manifest_documented_at is not None else None,
            "total_items": len(manifest),
            "total_quantity": total_quantity,
            "manifest": manifest
        }
    
    @staticmethod
    def get_damaged_cargo_report(container_id: str, db: Session) -> dict:
        """Get report of damaged/missing cargo."""
        try:
            container_uuid = uuid.UUID(container_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Container UUID format")
        
        problem_items = db.query(CargoItem).filter(
            CargoItem.container_id == container_uuid,
            CargoItem.condition.in_([CargoCondition.DAMAGED, CargoCondition.MISSING])
        ).all()
        
        issues = []
        for item in problem_items:
            issues.append({
                "cargo_id": str(item.id),
                "description": item.description,
                "quantity": item.quantity,
                "condition": item.condition.value,
                "notes": item.notes,
                "recorded_at": item.created_at.isoformat()
            })
        
        return {
            "container_id": container_id,
            "problem_items_count": len(issues),
            "has_issues": len(issues) > 0,
            "issues": issues
        }
