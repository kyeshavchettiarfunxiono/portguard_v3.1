"""
Service layer for unpacking workflow management.
"""
from typing import Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from typing import cast as py_cast
from fastapi import HTTPException

from models.unpacking import UnpackingSession, UnpackingStep
from models.container import Container, ContainerStatus
from schemas.unpacking import UnpackingSessionResponse


class UnpackingService:
    """Manages unpacking workflow sessions and step transitions."""
    
    @staticmethod
    def get_or_create_unpacking_session(
        container_id: UUID,
        db: Session,
        inspector_id: Optional[UUID] = None
    ) -> UnpackingSession:
        """Get existing unpacking session or create new one."""
        session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_id
        ).first()
        
        if not session:
            if not inspector_id:
                raise HTTPException(status_code=400, detail="Inspector ID is required to start unpacking")
            # Create new unpacking session
            session = UnpackingSession(
                container_id=container_id,
                current_step=UnpackingStep.EXTERIOR_INSPECTION,
                inspector_id=inspector_id,
                started_at=datetime.utcnow()
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        
        return session
    
    @staticmethod
    def advance_step(container_id: UUID, db: Session) -> UnpackingSession:
        """Move to next step in unpacking workflow."""
        session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Unpacking session not found")
        
        # Check if current step is complete
        if not session.can_move_to_next_step():
            current_step_val = py_cast(str, session.current_step.value if hasattr(session.current_step, 'value') else str(session.current_step))
            required = session.get_required_photos()[current_step_val]
            current = getattr(session, f'{current_step_val.lower()}_photos', 0)
            raise HTTPException(
                status_code=400,
                detail=f"Cannot advance: Need {required} photo(s) but have {current}"
            )
        
        # Move to next step
        steps = [e.value for e in UnpackingStep]
        current_step_val = py_cast(str, session.current_step.value if hasattr(session.current_step, 'value') else str(session.current_step))
        current_index = steps.index(current_step_val)
        
        if current_index >= len(steps) - 1:
            session.is_complete = True  # type: ignore
        else:
            next_step_value = steps[current_index + 1]

            cargo_completed_at = getattr(session, 'cargo_unloading_completed_at', None)
            if current_step_val == 'CARGO_UNLOADING' and cargo_completed_at is None:
                completed_at = datetime.utcnow()
                session.cargo_unloading_completed_at = completed_at  # type: ignore[assignment]
                cargo_started_at = getattr(session, 'cargo_unloading_started_at', None)
                if cargo_started_at is not None:
                    elapsed_minutes = max(
                        0,
                        int((completed_at - cargo_started_at).total_seconds() // 60)
                    )
                    session.cargo_unloading_duration_minutes = elapsed_minutes  # type: ignore[assignment]

            session.current_step = UnpackingStep[next_step_value]  # type: ignore

            cargo_started_at = getattr(session, 'cargo_unloading_started_at', None)
            if next_step_value == 'CARGO_UNLOADING' and cargo_started_at is None:
                session.cargo_unloading_started_at = datetime.utcnow()  # type: ignore[assignment]
                session.cargo_unloading_completed_at = None  # type: ignore[assignment]
                session.cargo_unloading_duration_minutes = None  # type: ignore[assignment]
        
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def record_photo(container_id: UUID, step: str, db: Session) -> UnpackingSession:
        """Increment photo count for a step."""
        session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Unpacking session not found")
        
        # Increment appropriate photo counter
        step_map = {
            'EXTERIOR_INSPECTION': 'exterior_inspection_photos',
            'DOOR_OPENING': 'door_opening_photos',
            'INTERIOR_INSPECTION': 'interior_inspection_photos',
            'CARGO_UNLOADING': 'cargo_unloading_photos',
            'CARGO_MANIFEST': 'cargo_items_count'
        }
        
        photo_field = step_map.get(step)
        if photo_field:
            current = getattr(session, photo_field, 0)
            setattr(session, photo_field, current + 1)
            db.commit()
            db.refresh(session)
        
        return session
    
    @staticmethod
    def add_cargo_item(container_id: UUID, db: Session) -> UnpackingSession:
        """Increment cargo items count."""
        session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Unpacking session not found")
        
        session.cargo_items_count = py_cast(int, (session.cargo_items_count or 0) + 1)  # type: ignore
        db.commit()
        db.refresh(session)
        return session

    @staticmethod
    def document_manifest(
        container_id: UUID,
        document_reference: Optional[str],
        manifest_notes: Optional[str],
        inspector_id: UUID,
        db: Session
    ) -> UnpackingSession:
        """Mark cargo manifest as documented with optional reference/notes."""
        session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_id
        ).first()

        if not session:
            raise HTTPException(status_code=404, detail="Unpacking session not found")

        session.manifest_document_reference = (document_reference or None)  # type: ignore
        session.manifest_notes = (manifest_notes or None)  # type: ignore
        session.manifest_complete = True  # type: ignore
        session.manifest_documented_at = datetime.utcnow()  # type: ignore
        session.manifest_documented_by = inspector_id  # type: ignore

        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def report_damage(
        container_id: UUID,
        description: str,
        damage_photo_count: int,
        db: Session
    ) -> UnpackingSession:
        """Record damage or discrepancies."""
        session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Unpacking session not found")
        
        session.damage_reported = True  # type: ignore
        session.damage_description = description  # type: ignore
        session.damage_photo_count = damage_photo_count  # type: ignore
        
        # Propagate damage alert to the Container model for Supervisor visibility
        container = db.query(Container).filter(Container.id == container_id).first()
        if container:
            container.needs_repair = True  # type: ignore
            container.repair_notes = f"Unpacking Damage: {description}"  # type: ignore
            
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def complete_unpacking(
        container_id: UUID,
        final_notes: Optional[str],
        user_id: UUID,
        db: Session
    ) -> UnpackingSession:
        """Complete unpacking workflow."""
        session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Unpacking session not found")
        
        container = db.query(Container).filter(Container.id == container_id).first()
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        # Check if final inspection is complete
        current_step_val = py_cast(str, session.current_step.value if hasattr(session.current_step, 'value') else str(session.current_step))
        if current_step_val != 'FINAL_INSPECTION':
            raise HTTPException(
                status_code=400,
                detail=f"Cannot complete: currently at {current_step_val}"
            )
        
        # Save final notes
        if final_notes:
            session.final_notes = final_notes  # type: ignore
        
        session.is_complete = True  # type: ignore
        
        # Transition container: UNPACKING -> PACKING (if was at REGISTERED) -> PENDING_REVIEW
        current_status = py_cast(ContainerStatus, container.status)
        if current_status == ContainerStatus.REGISTERED:
            container.transition_to(ContainerStatus.UNPACKING, user_id)
        
        # Now transition to PENDING_REVIEW
        container.transition_to(ContainerStatus.PENDING_REVIEW, user_id)
        
        db.commit()
        db.refresh(session)
        
        return session
    
    @staticmethod
    def revert_to_previous_step(container_id: UUID, db: Session) -> UnpackingSession:
        """Revert to the previous step in the unpacking workflow."""
        session = db.query(UnpackingSession).filter(
            UnpackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Unpacking session not found")
        
        steps = [e.value for e in UnpackingStep]
        current_step_val = py_cast(str, session.current_step.value if hasattr(session.current_step, 'value') else str(session.current_step))
        current_index = steps.index(current_step_val)
        
        if current_index <= 0:
            raise HTTPException(status_code=400, detail="Cannot go back from first step")
        
        # Clear photo count for current step before reverting
        if session.current_step.value == 'EXTERIOR_INSPECTION':
            session.exterior_inspection_photos = 0  # type: ignore
        elif session.current_step.value == 'DOOR_OPENING':
            session.door_opening_photos = 0  # type: ignore
        elif session.current_step.value == 'INTERIOR_INSPECTION':
            session.interior_inspection_photos = 0  # type: ignore
        elif session.current_step.value == 'CARGO_UNLOADING':
            session.cargo_unloading_photos = 0  # type: ignore
            session.cargo_unloading_started_at = None  # type: ignore[assignment]
            session.cargo_unloading_completed_at = None  # type: ignore[assignment]
            session.cargo_unloading_duration_minutes = None  # type: ignore[assignment]
        
        previous_step = UnpackingStep[steps[current_index - 1]]
        session.current_step = previous_step  # type: ignore
        
        db.commit()
        db.refresh(session)
        return session
