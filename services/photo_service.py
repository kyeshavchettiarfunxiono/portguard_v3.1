from models.container import Container, ContainerStatus

def get_photo_requirements(container_type: str) -> dict:
    """
    Returns photo requirements based on Port of Durban standards.
    20FT = 4 photos, 40FT/HC = 5 photos.
    """
    # Standardizing keys to match your Enum/Database values
    requirements = {
        "20FT": {
            "required_count": 4,
            "types": ['FRONT', 'BACK', 'SEAL', 'LOADING_POINT']
        },
        "40FT": {
            "required_count": 5,
            "types": ['FRONT', 'BACK', 'LEFT', 'RIGHT', 'SEAL']
        },
        "HC": {
            "required_count": 5,
            "types": ['FRONT', 'BACK', 'LEFT', 'RIGHT', 'SEAL']
        }
    }
    return requirements.get(container_type, requirements["40FT"])

def validate_container_evidence(container, images) -> dict:
    """Checks if all mandatory photo types exist for this specific container."""
    reqs = get_photo_requirements(container.type)
    uploaded_types = {img.image_type.upper() for img in images}
    required_types = set(reqs["types"])
    
    missing = required_types - uploaded_types
    return {
        "is_valid": len(missing) == 0,
        "missing_types": list(missing),
        "count": f"{len(uploaded_types)}/{reqs['required_count']}"
    }