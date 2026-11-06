
import os
from uuid import uuid4
from datetime import date, timedelta

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from main import app
from db.session import get_db
from models.user import User
from core.constants import UserRole


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

client = TestClient(app)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def unique_email():
    return f"worker_{uuid4().hex[:10]}@example.com"


def register_user(email=None):
    email = email or unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Field Worker",
            "email": email,
            "password": "StrongPass123!",
            "phone_number": "9876543210",
        },
    )

    assert response.status_code in (200, 201), response.text
    return email


def assign_role(email, role):
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.role = role
        user.is_active = True
        user.is_verified = True
        db.commit()
    finally:
        db.close()


def login_user(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def create_user_with_role(role):
    email = register_user()
    assign_role(email, role)
    token = login_user(email)

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user_id = str(user.id)
    finally:
        db.close()

    return {
        "email": email,
        "user_id": user_id,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def worker_payload(user_id, worker_code=None):
    return {
        "user_id": user_id,
        "worker_code": worker_code or f"WRK-{uuid4().hex[:8].upper()}",
        "phone": "9876543210",
        "address": "Hyderabad, Telangana",
        "emergency_contact_name": "Emergency Contact",
        "emergency_contact_phone": "9123456789",
        "joining_date": date.today().isoformat(),
        "notes": "Test field worker profile",
    }


def create_worker(headers=None, user=None, payload=None):
    user = user or create_user_with_role(UserRole.FIELD_WORKER)
    headers = headers or create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )["headers"]

    payload = payload or worker_payload(user["user_id"])

    response = client.post(
        "/api/v1/field-workers",
        json=payload,
        headers=headers,
    )

    return response, user, payload


def setup_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    drivers,
                    field_workers,
                    vehicles,
                    pickups,
                    customers,
                    waste_categories,
                    locations,
                    password_reset_tokens,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )


def teardown_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    drivers,
                    field_workers,
                    vehicles,
                    pickups,
                    customers,
                    waste_categories,
                    locations,
                    password_reset_tokens,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )

    app.dependency_overrides.clear()
    engine.dispose()


# CREATE FIELD WORKER TESTS

def test_management_can_create_field_worker():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    response, _, payload = create_worker(
        headers=manager["headers"],
        user=worker,
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == payload["user_id"]
    assert response.json()["worker_code"] == payload["worker_code"]


def test_create_field_worker_requires_authentication():
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    response = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
    )

    assert response.status_code in (401, 403)


def test_customer_cannot_create_field_worker():
    customer = create_user_with_role(UserRole.CUSTOMER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    response = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=customer["headers"],
    )

    assert response.status_code == 403


def test_cannot_create_worker_for_non_field_worker_user():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    customer = create_user_with_role(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/field-workers",
        json=worker_payload(customer["user_id"]),
        headers=manager["headers"],
    )

    assert response.status_code == 400


def test_duplicate_field_worker_profile_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)
    payload = worker_payload(worker["user_id"])

    first = client.post(
        "/api/v1/field-workers",
        json=payload,
        headers=manager["headers"],
    )

    second = client.post(
        "/api/v1/field-workers",
        json=payload,
        headers=manager["headers"],
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_duplicate_worker_code_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)

    first_worker = create_user_with_role(UserRole.FIELD_WORKER)
    second_worker = create_user_with_role(UserRole.FIELD_WORKER)

    code = f"WRK-{uuid4().hex[:8].upper()}"

    first = client.post(
        "/api/v1/field-workers",
        json=worker_payload(first_worker["user_id"], worker_code=code),
        headers=manager["headers"],
    )

    second = client.post(
        "/api/v1/field-workers",
        json=worker_payload(second_worker["user_id"], worker_code=code),
        headers=manager["headers"],
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_future_joining_date_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    payload = worker_payload(worker["user_id"])
    payload["joining_date"] = (
        date.today() + timedelta(days=10)
    ).isoformat()

    response = client.post(
        "/api/v1/field-workers",
        json=payload,
        headers=manager["headers"],
    )

    assert response.status_code == 422


def test_worker_code_is_normalized():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    payload = worker_payload(worker["user_id"])
    payload["worker_code"] = "  wrk test 101  "

    response = client.post(
        "/api/v1/field-workers",
        json=payload,
        headers=manager["headers"],
    )

    assert response.status_code == 201
    assert response.json()["worker_code"] == "WRKTEST101"


def test_invalid_phone_number_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    payload = worker_payload(worker["user_id"])
    payload["phone"] = "123"

    response = client.post(
        "/api/v1/field-workers",
        json=payload,
        headers=manager["headers"],
    )

    assert response.status_code == 422


# GET FIELD WORKER TESTS

def test_field_worker_can_view_own_profile():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=manager["headers"],
    )

    assert created.status_code == 201

    response = client.get(
        "/api/v1/field-workers/me",
        headers=worker["headers"],
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == worker["user_id"]


def test_field_worker_cannot_view_another_worker_profile():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    first_worker = create_user_with_role(UserRole.FIELD_WORKER)
    second_worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(second_worker["user_id"]),
        headers=manager["headers"],
    )

    assert created.status_code == 201

    response = client.get(
        f"/api/v1/field-workers/{created.json()['id']}",
        headers=first_worker["headers"],
    )

    assert response.status_code == 403


def test_management_can_list_field_workers():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=manager["headers"],
    )

    assert created.status_code == 201

    response = client.get(
        "/api/v1/field-workers",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert any(
        item["id"] == created.json()["id"]
        for item in response.json()
    )


def test_field_worker_cannot_list_all_workers():
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    response = client.get(
        "/api/v1/field-workers",
        headers=worker["headers"],
    )

    assert response.status_code == 403


def test_get_nonexistent_field_worker_returns_404():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)

    response = client.get(
        f"/api/v1/field-workers/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404


# UPDATE FIELD WORKER TESTS

def test_management_can_update_field_worker():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=manager["headers"],
    )

    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/field-workers/{created.json()['id']}",
        json={
            "phone": "9123456789",
            "address": "Secunderabad",
            "emergency_contact_name": "Updated Contact",
        },
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "9123456789"
    assert response.json()["address"] == "Secunderabad"


def test_empty_field_worker_update_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/field-workers/{created.json()['id']}",
        json={},
        headers=manager["headers"],
    )

    assert response.status_code == 400


def test_field_worker_cannot_update_own_profile():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/field-workers/{created.json()['id']}",
        json={"phone": "9123456789"},
        headers=worker["headers"],
    )

    assert response.status_code == 403


# FIELD WORKER STATUS TESTS

def test_management_can_update_field_worker_status():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/field-workers/{created.json()['id']}/status",
        json={
            "status": "inactive",
            "availability": "unavailable",
        },
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert response.json()["availability"] == "unavailable"


def test_invalid_field_worker_status_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/field-workers/{created.json()['id']}/status",
        json={"status": "invalid_status"},
        headers=manager["headers"],
    )

    assert response.status_code == 422


def test_field_worker_cannot_update_worker_status():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    worker = create_user_with_role(UserRole.FIELD_WORKER)

    created = client.post(
        "/api/v1/field-workers",
        json=worker_payload(worker["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/field-workers/{created.json()['id']}/status",
        json={"status": "inactive"},
        headers=worker["headers"],
    )

    assert response.status_code == 403
