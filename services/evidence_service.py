# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 

import uuid
import shutil
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from models.container import Container, ContainerType
from models.evidence import ContainerImage
from services.photo_service import get_photo_requirements

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Mandatory photo counts by container type
MANDATORY_PHOTO_COUNTS = {
    ContainerType.TWENTY_FT: 4,
    ContainerType.FORTY_FT: 5,
    ContainerType.HC: 5
}


class EvidenceService:
    """Service layer for evidence (photo) management."""
    
    @staticmethod
    def upload_container_image(
        container_id: str,
        image_type: str,
        file: UploadFile,
        user_id: Optional[uuid.UUID],
        db: Session
    ) -> dict:
        """Upload and store container image."""
        try:
            container_uuid = uuid.UUID(container_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Container UUID format")
        
        # Verify container exists
        container = db.query(Container).filter(Container.id == container_uuid).first()
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        # Generate filename
        original_filename = file.filename if file.filename else "unknown.jpg"
        file_extension = Path(original_filename).suffix
        file_name = f"{image_type}_{uuid.uuid4()}{file_extension}"
        
        # Create container directory
        container_path = UPLOAD_DIR / container_id
        container_path.mkdir(exist_ok=True)
        save_path = container_path / file_name
        
        # Save file
        with save_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Record in database
        new_image = ContainerImage(
            container_id=container_uuid,
            file_path=str(save_path),
            image_type=image_type.upper(),
            created_by=user_id
        )
        db.add(new_image)
        db.commit()
        
        return {"message": "Upload successful", "path": str(save_path), "type": image_type}
    
    @staticmethod
    def validate_evidence(
        container_id: str,
        db: Session
    ) -> dict:
        """Validate container evidence completeness."""
        try:
            container_uuid = uuid.UUID(container_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Container UUID format")
        
        container = db.query(Container).filter(Container.id == container_uuid).first()
        if not container:
            raise HTTPException(status_code=404, detail="Container not found")
        
        images = db.query(ContainerImage).filter(
            ContainerImage.container_id == container_uuid
        ).all()

        container_type = container.type.value if hasattr(container.type, "value") else str(container.type)
        requirements = get_photo_requirements(container_type)
        required_types = requirements["types"]
        required_count = requirements["required_count"]

        packing_step_types = {"BEFORE_PACKING", "CARGO_PHOTOS", "AFTER_PACKING", "SEALING"}
        found_types = set()

        for image in images:
            img_type = image.image_type.upper()
            if img_type in required_types:
                found_types.add(img_type)
                continue
            if img_type == "SEALING" and "SEAL" in required_types:
                found_types.add("SEAL")
                continue
            if img_type in packing_step_types:
                for required in required_types:
                    if required == "SEAL":
                        continue
                    if required not in found_types:
                        found_types.add(required)
                        break

        missing_types = [req for req in required_types if req not in found_types]
        is_valid = len(missing_types) == 0

        return {
            "container_id": container_id,
            "container_type": container_type,
            "required_photos": required_count,
            "uploaded_photos": len(images),
            "is_valid": is_valid,
            "missing_count": len(missing_types),
            "missing_types": missing_types
        }
    
    @staticmethod
    def can_close_container(container_id: str, db: Session) -> dict:
        """Check if container meets closure requirements (State Machine)."""
        validation = EvidenceService.validate_evidence(container_id, db)
        
        return {
            "container_id": container_id,
            "can_close": validation["is_valid"],
            "validation_status": validation,
            "message": "All required photos present. Container can be closed." if validation["is_valid"]
                      else f"Missing {validation['missing_count']} photos. Cannot close."
        }
    
    @staticmethod
    def get_missing_evidence_types(
        container_id: str,
        db: Session
    ) -> list:
        """Get list of missing photo types for a container."""
        validation = EvidenceService.validate_evidence(container_id, db)
        return validation.get("missing_types", [])
