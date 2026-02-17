# Software Engineer: Kyeshav Chettiar 
# Company FXO - Adcorp 
# Configured and pushed onto the virtual machine for testing and evaluation for team members to use within the companies rules and regulations 
# v3.0.0.0 
# Docker Configured & new project directory has been created for this version on github at the following link: 



from sqlalchemy import Column, String, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from core.database import Base

class ContainerImage(Base):
    __tablename__ = "container_images"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    container_id = Column(UUID(as_uuid=True), ForeignKey("containers.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Store the path: e.g., "uploads/MSMU4557285/front_view.jpg"
    file_path = Column(String, nullable=False)
    image_type = Column(String, nullable=False) # e.g., 'FRONT', 'BACK', 'SEAL'
    
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())