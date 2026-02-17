import io
import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.compiler import compiles

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import app
from core.database import Base, get_db
from core.security import get_current_user

# Ensure models are registered with SQLAlchemy metadata
import models.user  # noqa: F401
import models.booking  # noqa: F401
import models.container  # noqa: F401
import models.evidence  # noqa: F401
import models.packing  # noqa: F401
import models.downtime  # noqa: F401

from models.container import Container, ContainerStatus
from services.container_service import ContainerService


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kwargs):
    return "CHAR(36)"


class MockUser:
    def __init__(self, role: str) -> None:
        self.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        self.role = role
        self.email = "test@example.com"
        self.username = "test-user"


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: MockUser("ADMIN")

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def create_booking(client: TestClient, suffix: int) -> str:
    payload = {
        "booking_reference": f"BOOK{suffix:04d}",
        "client": "TEST_CLIENT",
        "vessel_name": "TEST_VESSEL",
        "container_type": "HC"
    }
    response = client.post("/api/bookings/", json=payload)
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


def create_hc_container(client: TestClient, booking_id: str, suffix: int) -> str:
    payload = {
        "container_no": f"TEST{suffix:07d}",
        "booking_id": booking_id,
        "type": "HC"
    }
    response = client.post("/api/containers/", json=payload)
    assert response.status_code in (200, 201), response.text
    return response.json()["id"]


def upload_photo(client: TestClient, container_id: str, image_type: str) -> None:
    file_content = io.BytesIO(b"test-image")
    files = {"file": ("photo.jpg", file_content, "image/jpeg")}
    response = client.post(
        f"/api/containers/{container_id}/upload-image/",
        params={"image_type": image_type},
        files=files
    )
    assert response.status_code in (200, 201), response.text


def update_status(client: TestClient, container_id: str, status: str):
    response = client.put(
        f"/api/containers/{container_id}/status",
        json={"status": status}
    )
    return response


def test_1_register_container_persistence(client: TestClient, db_session):
    booking_id = create_booking(client, 1)
    container_id = create_hc_container(client, booking_id, 1)

    record = db_session.query(Container).filter(
        Container.id == uuid.UUID(container_id)
    ).first()
    assert record is not None


def test_2_rule_of_5_blocks_pending_review_with_4_photos(client: TestClient):
    booking_id = create_booking(client, 2)
    container_id = create_hc_container(client, booking_id, 2)

    response = update_status(client, container_id, "PACKING")
    assert response.status_code in (200, 201), response.text

    for image_type in ["FRONT", "BACK", "LEFT", "RIGHT"]:
        upload_photo(client, container_id, image_type)

    response = update_status(client, container_id, "PENDING_REVIEW")
    assert response.status_code == 400


def test_3_commercial_math_1_5_hours_is_375():
    assert ContainerService.calculate_total_downtime_cost(1.5) == 375.0


def test_4_supervisor_finalization_updates_status(client: TestClient, db_session):
    app.dependency_overrides[get_current_user] = lambda: MockUser("SUPERVISOR")

    booking_id = create_booking(client, 3)
    container_id = create_hc_container(client, booking_id, 3)

    for image_type in ["FRONT", "BACK", "LEFT", "RIGHT", "SEAL"]:
        upload_photo(client, container_id, image_type)

    record = db_session.query(Container).filter(
        Container.id == uuid.UUID(container_id)
    ).first()
    assert record is not None
    record.status = ContainerStatus.PENDING_REVIEW
    db_session.commit()

    response = client.post(f"/api/containers/{container_id}/finalize-arrival")
    assert response.status_code in (200, 201), response.text

    record = db_session.query(Container).filter(
        Container.id == uuid.UUID(container_id)
    ).first()
    assert record is not None
    status_value = record.status.value if hasattr(record.status, "value") else str(record.status)
    assert status_value == ContainerStatus.FINALIZED.value
