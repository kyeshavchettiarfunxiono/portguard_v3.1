"""
Service layer for packing workflow management.
"""
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from typing import cast as py_cast
from fastapi import HTTPException

from models.packing import PackingSession, PackingStep
from models.container import Container, ContainerStatus
from schemas.packing import PackingSessionResponse


class PackingService:
    """Manages packing workflow sessions and step transitions."""

    @staticmethod
    def _get_container_type_value(container: Container) -> str:
        return container.type.value if hasattr(container.type, "value") else str(container.type)
    
    @staticmethod
    def get_or_create_packing_session(container_id: UUID, db: Session) -> PackingSession:
        """Get existing packing session or create new one."""
        session = db.query(PackingSession).filter(
            PackingSession.container_id == container_id
        ).first()
        
        if not session:
            session = PackingSession(container_id=container_id)
            db.add(session)
            db.commit()
            db.refresh(session)
        
        return session
    
    @staticmethod
    def get_packing_session(container_id: UUID, db: Session) -> PackingSession:
        """Get packing session for a container."""
        session = db.query(PackingSession).filter(
            PackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Packing session not found")
        
        return session
    
    @staticmethod
    def record_photos(
        container_id: UUID,
        step: PackingStep,
        photo_count: int,
        db: Session
    ) -> PackingSession:
        """Record photos uploaded for a specific step."""
        session = PackingService.get_packing_session(container_id, db)
        container = db.query(Container).filter(Container.id == container_id).first()
        
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        container_type = PackingService._get_container_type_value(container)
        
        # Update photo counts based on step
        if step == PackingStep.BEFORE_PACKING:
            session.before_packing_photos = (session.before_packing_photos or 0) + photo_count  # type: ignore
        elif step == PackingStep.CARGO_PHOTOS:
            session.cargo_photos = (session.cargo_photos or 0) + photo_count  # type: ignore
        elif step == PackingStep.AFTER_PACKING:
            session.after_packing_photos = (session.after_packing_photos or 0) + photo_count  # type: ignore
        elif step == PackingStep.SEALING:
            session.seal_photo_count = (session.seal_photo_count or 0) + photo_count  # type: ignore
        
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def can_advance_step(container_id: UUID, db: Session) -> bool:
        """Check if container can advance to next step."""
        session = PackingService.get_packing_session(container_id, db)
        container = db.query(Container).filter(Container.id == container_id).first()
        
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        container_type = PackingService._get_container_type_value(container)
        return session.can_move_to_next_step(container_type)
    
    @staticmethod
    def advance_step(container_id: UUID, db: Session) -> PackingSession:
        """Move packing session to next step."""
        session = PackingService.get_packing_session(container_id, db)
        container = db.query(Container).filter(Container.id == container_id).first()
        
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        container_type = PackingService._get_container_type_value(container)
        
        if not session.can_move_to_next_step(container_type):
            current_step = py_cast(PackingStep, session.current_step)
            step_name = current_step.value
            required = session.get_required_photos(container_type)
            required_count = required.get(step_name, 1)
            
            photo_map = {
                'BEFORE_PACKING': session.before_packing_photos,
                'CARGO_PHOTOS': session.cargo_photos,
                'AFTER_PACKING': session.after_packing_photos,
                'SEALING': session.seal_photo_count
            }
            
            current_count = photo_map.get(step_name, 0)
            
            raise HTTPException(
                status_code=400,
                detail=f"Step not complete. Need {required_count} photos, have {current_count}. "
                        f"{'Also need seal number.' if step_name == 'SEALING' else ''}"
            )
        
        session.move_to_next_step()
        db.commit()
        db.refresh(session)
        return session
    
    @staticmethod
    def complete_packing(
        container_id: UUID,
        seal_number: str,
        gross_mass: Optional[str],
        tare_weight: Optional[str],
        user_id: Optional[UUID],
        db: Session
    ) -> PackingSession:
        """Complete packing workflow and transition container status."""
        session = PackingService.get_packing_session(container_id, db)
        container = db.query(Container).filter(Container.id == container_id).first()
        
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        container_type = PackingService._get_container_type_value(container)
        current_step = py_cast(PackingStep, session.current_step)
        
        if current_step != PackingStep.SEALING:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot seal: container is at step {current_step.value}, not SEALING"
            )
        
        # Validate seal number is provided
        if not seal_number or not seal_number.strip():
            raise HTTPException(
                status_code=400,
                detail="Seal number is required"
            )
        
        # Update sealing info first
        session.seal_number = seal_number  # type: ignore
        if gross_mass:
            session.gross_mass = gross_mass  # type: ignore
        if tare_weight:
            session.tare_weight = tare_weight  # type: ignore
        
        # Now check if step is complete with updated seal number
        if not session.is_step_complete(container_type):
            required_photos = session.get_required_photos(container_type).get('SEALING', 1)
            raise HTTPException(
                status_code=400,
                detail=f"Sealing step incomplete: Need {required_photos} seal photo(s) but have {session.seal_photo_count or 0}. Make sure you uploaded the seal photo before clicking Complete."
            )
        
        # Transition container: REGISTERED -> PACKING -> PENDING_REVIEW
        current_status = py_cast(ContainerStatus, container.status)
        if current_status == ContainerStatus.REGISTERED:
            container.transition_to(ContainerStatus.PACKING, user_id)
        
        # Now transition to PENDING_REVIEW
        container.transition_to(ContainerStatus.PENDING_REVIEW, user_id)
        
        db.commit()
        db.refresh(session)
        
        return session
    
    @staticmethod
    def get_step_progress(container_id: UUID, db: Session) -> dict:
        """Get detailed progress information for current step."""
        session = PackingService.get_packing_session(container_id, db)
        container = db.query(Container).filter(Container.id == container_id).first()
        
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        container_type = PackingService._get_container_type_value(container)
        current_step = py_cast(PackingStep, session.current_step)
        
        step_name = current_step.value
        required = session.get_required_photos(container_type)
        required_count = required.get(step_name, 1)
        
        photo_map = {
            'BEFORE_PACKING': session.before_packing_photos,
            'CARGO_PHOTOS': session.cargo_photos,
            'AFTER_PACKING': session.after_packing_photos,
            'SEALING': session.seal_photo_count
        }
        
        current_count = photo_map.get(step_name, 0)
        is_complete = session.is_step_complete(container_type)
        
        # Calculate overall progress (4 steps total)
        steps = ['BEFORE_PACKING', 'CARGO_PHOTOS', 'AFTER_PACKING', 'SEALING']
        current_step_index = steps.index(step_name)
        
        return {
            'current_step': step_name,
            'step_number': current_step_index + 1,
            'total_steps': 4,
            'required_photos': required_count,
            'current_photos': current_count,
            'is_complete': is_complete,
            'progress_percent': ((current_step_index + 1) / 4) * 100,
            'container_type': container_type,
            'seal_number': session.seal_number,
            'before_packing_photos': session.before_packing_photos or 0,
            'cargo_photos': session.cargo_photos or 0,
            'after_packing_photos': session.after_packing_photos or 0,
            'seal_photo_count': session.seal_photo_count or 0
        }

    @staticmethod
    def pause_and_release(container_id: UUID, db: Session) -> dict:
        """
        Pause packing session and release container for handover.
        All progress is saved automatically. Container remains in PACKING state
        but becomes available in the Ready for Work queue.
        """
        container = db.query(Container).filter(Container.id == container_id).first()
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        session = db.query(PackingSession).filter(
            PackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Packing session not found")
        
        # Get current progress
        current_step = py_cast(PackingStep, session.current_step)
        step_index = ['BEFORE_PACKING', 'CARGO_PHOTOS', 'AFTER_PACKING', 'SEALING'].index(current_step.value)
        
        return {
            'status': 'paused',
            'container_id': str(container_id),
            'current_step': current_step.value,
            'step_number': step_index + 1,
            'message': f'Container paused at Step {step_index + 1}. Progress saved. Container available for handover.',
            'before_packing_photos': session.before_packing_photos or 0,
            'cargo_photos': session.cargo_photos or 0,
            'after_packing_photos': session.after_packing_photos or 0,
            'seal_photo_count': session.seal_photo_count or 0
        }
    @staticmethod
    def revert_to_previous_step(container_id: UUID, db: Session) -> PackingSession:
        """
        Revert to the previous step in the packing workflow.
        Clears photo count for the current step.
        """
        session = db.query(PackingSession).filter(
            PackingSession.container_id == container_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Packing session not found")
        
        current_step = py_cast(PackingStep, session.current_step)
        steps = ['BEFORE_PACKING', 'CARGO_PHOTOS', 'AFTER_PACKING', 'SEALING']
        current_index = steps.index(current_step.value)
        
        if current_index <= 0:
            raise HTTPException(status_code=400, detail="Cannot go back from first step")
        
        # Clear photo count for current step before reverting
        if current_step.value == 'BEFORE_PACKING':
            session.before_packing_photos = 0  # type: ignore
        elif current_step.value == 'CARGO_PHOTOS':
            session.cargo_photos = 0  # type: ignore
        elif current_step.value == 'AFTER_PACKING':
            session.after_packing_photos = 0  # type: ignore
        elif current_step.value == 'SEALING':
            session.seal_photo_count = 0  # type: ignore
        
        # Go back to previous step
        previous_step = PackingStep[steps[current_index - 1]]
        session.current_step = previous_step
        
        db.commit()
        db.refresh(session)
        
        return session