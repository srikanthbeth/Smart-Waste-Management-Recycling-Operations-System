
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
    return f"driver_{uuid4().hex[:10]}@example.com"


def register_user(email=None):
    email = email or unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Driver",
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


def driver_payload(user_id, driver_code=None, license_number=None):
    return {
        "user_id": user_id,
        "driver_code": driver_code or f"DRV-{uuid4().hex[:8].upper()}",
        "license_number": license_number or f"DL-{uuid4().hex[:10].upper()}",
        "license_type": "LMV",
        "license_expiry_date": (date.today() + timedelta(days=365)).isoformat(),
        "phone": "9876543210",
        "address": "Hyderabad, Telangana",
        "joining_date": date.today().isoformat(),
        "notes": "Test driver profile",
    }


def create_driver(headers=None, user=None, payload=None):
    user = user or create_user_with_role(UserRole.DRIVER)
    headers = headers or create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )["headers"]

    payload = payload or driver_payload(user["user_id"])

    response = client.post(
        "/api/v1/drivers",
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


# CREATE DRIVER TESTS

def test_management_can_create_driver():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    response, _, payload = create_driver(
        headers=manager["headers"],
        user=driver,
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == payload["user_id"]
    assert response.json()["driver_code"] == payload["driver_code"]


def test_create_driver_requires_authentication():
    driver = create_user_with_role(UserRole.DRIVER)

    response = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
    )

    assert response.status_code in (401, 403)


def test_customer_cannot_create_driver():
    customer = create_user_with_role(UserRole.CUSTOMER)
    driver = create_user_with_role(UserRole.DRIVER)

    response = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=customer["headers"],
    )

    assert response.status_code == 403


def test_cannot_create_driver_for_non_driver_user():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    customer = create_user_with_role(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/drivers",
        json=driver_payload(customer["user_id"]),
        headers=manager["headers"],
    )

    assert response.status_code == 400


def test_duplicate_driver_profile_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)
    payload = driver_payload(driver["user_id"])

    first = client.post(
        "/api/v1/drivers",
        json=payload,
        headers=manager["headers"],
    )

    second = client.post(
        "/api/v1/drivers",
        json=payload,
        headers=manager["headers"],
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_duplicate_driver_code_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)

    first_user = create_user_with_role(UserRole.DRIVER)
    second_user = create_user_with_role(UserRole.DRIVER)

    code = f"DRV-{uuid4().hex[:8].upper()}"

    first = client.post(
        "/api/v1/drivers",
        json=driver_payload(first_user["user_id"], driver_code=code),
        headers=manager["headers"],
    )

    second = client.post(
        "/api/v1/drivers",
        json=driver_payload(second_user["user_id"], driver_code=code),
        headers=manager["headers"],
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_duplicate_license_number_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)

    first_user = create_user_with_role(UserRole.DRIVER)
    second_user = create_user_with_role(UserRole.DRIVER)

    license_number = f"DL-{uuid4().hex[:10].upper()}"

    first = client.post(
        "/api/v1/drivers",
        json=driver_payload(
            first_user["user_id"],
            license_number=license_number,
        ),
        headers=manager["headers"],
    )

    second = client.post(
        "/api/v1/drivers",
        json=driver_payload(
            second_user["user_id"],
            license_number=license_number,
        ),
        headers=manager["headers"],
    )

    assert first.status_code == 201
    assert second.status_code == 409


def test_expired_driver_license_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    payload = driver_payload(driver["user_id"])
    payload["license_expiry_date"] = (
        date.today() - timedelta(days=1)
    ).isoformat()

    response = client.post(
        "/api/v1/drivers",
        json=payload,
        headers=manager["headers"],
    )

    assert response.status_code == 422


def test_future_joining_date_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    payload = driver_payload(driver["user_id"])
    payload["joining_date"] = (
        date.today() + timedelta(days=10)
    ).isoformat()

    response = client.post(
        "/api/v1/drivers",
        json=payload,
        headers=manager["headers"],
    )

    assert response.status_code == 422


def test_driver_code_is_normalized():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    payload = driver_payload(driver["user_id"])
    payload["driver_code"] = "  drv test 101  "

    response = client.post(
        "/api/v1/drivers",
        json=payload,
        headers=manager["headers"],
    )

    assert response.status_code == 201
    assert response.json()["driver_code"] == "DRVTEST101"


# GET DRIVER TESTS

def test_driver_can_view_own_profile():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=manager["headers"],
    )

    assert created.status_code == 201

    response = client.get(
        "/api/v1/drivers/me",
        headers=driver["headers"],
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == driver["user_id"]


def test_driver_cannot_view_another_driver_profile():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    first_driver = create_user_with_role(UserRole.DRIVER)
    second_driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(second_driver["user_id"]),
        headers=manager["headers"],
    )

    assert created.status_code == 201

    response = client.get(
        f"/api/v1/drivers/{created.json()['id']}",
        headers=first_driver["headers"],
    )

    assert response.status_code == 403


def test_management_can_list_drivers():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=manager["headers"],
    )

    assert created.status_code == 201

    response = client.get(
        "/api/v1/drivers",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert any(
        item["id"] == created.json()["id"]
        for item in response.json()
    )


def test_driver_cannot_list_all_drivers():
    driver = create_user_with_role(UserRole.DRIVER)

    response = client.get(
        "/api/v1/drivers",
        headers=driver["headers"],
    )

    assert response.status_code == 403


def test_get_nonexistent_driver_returns_404():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)

    response = client.get(
        f"/api/v1/drivers/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404


# UPDATE DRIVER TESTS

def test_management_can_update_driver():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=manager["headers"],
    )

    assert created.status_code == 201

    response = client.patch(
        f"/api/v1/drivers/{created.json()['id']}",
        json={"phone": "9123456789", "address": "Secunderabad"},
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "9123456789"
    assert response.json()["address"] == "Secunderabad"


def test_empty_driver_update_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/drivers/{created.json()['id']}",
        json={},
        headers=manager["headers"],
    )

    assert response.status_code == 400


def test_driver_cannot_update_own_profile():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/drivers/{created.json()['id']}",
        json={"phone": "9123456789"},
        headers=driver["headers"],
    )

    assert response.status_code == 403


def test_duplicate_license_number_on_update_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    first_driver = create_user_with_role(UserRole.DRIVER)
    second_driver = create_user_with_role(UserRole.DRIVER)

    first = client.post(
        "/api/v1/drivers",
        json=driver_payload(first_driver["user_id"]),
        headers=manager["headers"],
    )

    second = client.post(
        "/api/v1/drivers",
        json=driver_payload(second_driver["user_id"]),
        headers=manager["headers"],
    )

    assert first.status_code == 201
    assert second.status_code == 201

    response = client.patch(
        f"/api/v1/drivers/{second.json()['id']}",
        json={"license_number": first.json()["license_number"]},
        headers=manager["headers"],
    )

    assert response.status_code == 409


# DRIVER STATUS TESTS

def test_management_can_update_driver_status():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/drivers/{created.json()['id']}/status",
        json={
            "status": "inactive",
            "availability": "unavailable",
        },
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert response.json()["availability"] == "unavailable"


def test_invalid_driver_status_rejected():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/drivers/{created.json()['id']}/status",
        json={"status": "invalid_status"},
        headers=manager["headers"],
    )

    assert response.status_code == 422


def test_driver_cannot_update_driver_status():
    manager = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    driver = create_user_with_role(UserRole.DRIVER)

    created = client.post(
        "/api/v1/drivers",
        json=driver_payload(driver["user_id"]),
        headers=manager["headers"],
    )

    response = client.patch(
        f"/api/v1/drivers/{created.json()['id']}/status",
        json={"status": "inactive"},
        headers=driver["headers"],
    )

    assert response.status_code == 403
