from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.container import Container
from models.container_plan import ContainerPlan


class ContainerPlanService:
    @staticmethod
    def get_plan(container_id: UUID, db: Session) -> ContainerPlan:
        plan = db.query(ContainerPlan).filter(ContainerPlan.container_id == container_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Container planning record not found")
        return plan

    @staticmethod
    def upsert_plan(
        container_id: UUID,
        stack_priority: int,
        yard_zone: str | None,
        planned_date: datetime | None,
        plan_notes: str | None,
        user_id: UUID,
        db: Session,
    ) -> ContainerPlan:
        container = db.query(Container).filter(Container.id == container_id).first()
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")

        plan = db.query(ContainerPlan).filter(ContainerPlan.container_id == container_id).first()
        if not plan:
            plan = ContainerPlan(
                container_id=container_id,
                stack_priority=stack_priority,
                yard_zone=yard_zone,
                planned_date=planned_date,
                plan_notes=plan_notes,
                created_by=user_id,
                modified_by=user_id,
            )
            db.add(plan)
        else:
            setattr(plan, "stack_priority", stack_priority)
            setattr(plan, "yard_zone", yard_zone)
            setattr(plan, "planned_date", planned_date)
            setattr(plan, "plan_notes", plan_notes)
            setattr(plan, "modified_by", user_id)

        db.commit()
        db.refresh(plan)
        return plan

    @staticmethod
    def delete_plan(container_id: UUID, db: Session) -> None:
        plan = db.query(ContainerPlan).filter(ContainerPlan.container_id == container_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Container planning record not found")
        db.delete(plan)
        db.commit()
