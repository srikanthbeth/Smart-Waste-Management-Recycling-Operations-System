
import os
from uuid import uuid4

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
    expire_on_commit=False,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


# ---------------------------------------------------------
# COMMON HELPERS
# ---------------------------------------------------------

def unique_email():
    return f"recycling_{uuid4().hex[:10]}@example.com"


def register_user(role):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"Recycling {role.value}",
            "email": email,
            "password": "StrongPass123!",
            "phone_number": "9876543210",
        },
    )

    assert response.status_code in (200, 201), response.text

    db = TestingSessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        assert user is not None

        user.role = role
        user.is_active = True
        user.is_verified = True

        db.commit()

        user_id = str(user.id)

    finally:
        db.close()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "StrongPass123!",
        },
    )

    assert login_response.status_code == 200, (
        login_response.text
    )

    token = login_response.json()["access_token"]

    return {
        "email": email,
        "user_id": user_id,
        "token": token,
        "headers": {
            "Authorization": f"Bearer {token}"
        },
    }


def create_location(manager):
    response = client.post(
        "/api/v1/locations",
        headers=manager["headers"],
        json={
            "name": f"Recycling Zone {uuid4().hex[:6]}",
            "code": f"ZONE-{uuid4().hex[:8].upper()}",
            "location_type": "zone",
            "description": "Recycling center test zone",
            "city": "Hyderabad",
            "state": "Telangana",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_waste_category(manager):
    response = client.post(
        "/api/v1/waste-categories",
        headers=manager["headers"],
        json={
            "name": f"Recycling Waste {uuid4().hex[:6]}",
            "code": f"CAT-{uuid4().hex[:8].upper()}",
            "description": "Recycling center test category",
            "is_recyclable": True,
            "is_hazardous": False,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_center_payload(manager, **overrides):
    location = create_location(manager)
    category = create_waste_category(manager)

    payload = {
        "name": f"Recycling Center {uuid4().hex[:8]}",
        "code": f"RC-{uuid4().hex[:8].upper()}",
        "description": "Test recycling center",
        "location_id": location["id"],
        "manager_user_id": manager["user_id"],
        "processing_capacity_kg_per_day": 1000,
        "is_available": True,
        "accepted_waste_category_ids": [
            category["id"]
        ],
    }

    payload.update(overrides)

    return payload


def create_center(manager, **overrides):
    payload = create_center_payload(
        manager,
        **overrides,
    )

    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text

    return response.json()


def setup_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    recycling_center_waste_categories,
                    recycling_centers,
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
                    recycling_center_waste_categories,
                    recycling_centers,
                    waste_categories,
                    locations,
                    password_reset_tokens,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )

    engine.dispose()


# ---------------------------------------------------------
# CREATE RECYCLING CENTER TESTS
# ---------------------------------------------------------

def test_operations_manager_can_create_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    payload = create_center_payload(manager)

    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["name"] == payload["name"]
    assert data["code"] == payload["code"]
    assert data["location_id"] == payload["location_id"]
    assert data["manager_user_id"] == manager["user_id"]
    assert float(data["processing_capacity_kg_per_day"]) == 1000
    assert data["is_available"] is True
    assert data["status"] == "active"
    assert payload["accepted_waste_category_ids"][0] in (
        data["accepted_waste_category_ids"]
    )


def test_super_admin_can_create_recycling_center():
    admin = register_user(UserRole.SUPER_ADMIN)

    payload = create_center_payload(admin)

    response = client.post(
        "/api/v1/recycling-centers",
        headers=admin["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text


def test_recycling_center_requires_authentication():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    payload = create_center_payload(manager)

    response = client.post(
        "/api/v1/recycling-centers",
        json=payload,
    )

    assert response.status_code == 401


def test_customer_cannot_create_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)

    payload = create_center_payload(manager)

    response = client.post(
        "/api/v1/recycling-centers",
        headers=customer["headers"],
        json=payload,
    )

    assert response.status_code == 403


def test_duplicate_recycling_center_name_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    payload = create_center_payload(manager)

    first = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=payload,
    )

    assert first.status_code == 201, first.text

    second_payload = create_center_payload(
        manager,
        name=payload["name"],
    )

    second = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=second_payload,
    )

    assert second.status_code == 400
    assert "name already exists" in (
        second.json()["detail"].lower()
    )


def test_duplicate_recycling_center_code_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    payload = create_center_payload(manager)

    first = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=payload,
    )

    assert first.status_code == 201, first.text

    second_payload = create_center_payload(
        manager,
        code=payload["code"],
    )

    second = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=second_payload,
    )

    assert second.status_code == 400
    assert "code already exists" in (
        second.json()["detail"].lower()
    )


def test_recycling_center_requires_valid_location():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    payload = create_center_payload(
        manager,
        location_id=str(uuid4()),
    )

    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 404
    assert "location not found" in (
        response.json()["detail"].lower()
    )


def test_recycling_center_requires_valid_manager():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    payload = create_center_payload(
        manager,
        manager_user_id=str(uuid4()),
    )

    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 404
    assert "manager user not found" in (
        response.json()["detail"].lower()
    )


def test_recycling_center_requires_valid_waste_categories():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    payload = create_center_payload(
        manager,
        accepted_waste_category_ids=[str(uuid4())],
    )

    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 404
    assert "waste categories not found" in (
        response.json()["detail"].lower()
    )


def test_recycling_center_capacity_must_be_positive():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    payload = create_center_payload(
        manager,
        processing_capacity_kg_per_day=0,
    )

    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# GET AND LIST RECYCLING CENTER TESTS
# ---------------------------------------------------------

def test_management_can_get_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    response = client.get(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == center["id"]


def test_nonexistent_recycling_center_returns_404():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    response = client.get(
        f"/api/v1/recycling-centers/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404


def test_management_can_list_recycling_centers():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    create_center(manager)
    create_center(manager)

    response = client.get(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_customer_cannot_list_recycling_centers():
    customer = register_user(UserRole.CUSTOMER)

    response = client.get(
        "/api/v1/recycling-centers",
        headers=customer["headers"],
    )

    assert response.status_code == 403


def test_customer_can_view_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)

    center = create_center(manager)

    response = client.get(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=customer["headers"],
    )

    assert response.status_code == 200


# ---------------------------------------------------------
# UPDATE RECYCLING CENTER TESTS
# ---------------------------------------------------------

def test_management_can_update_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=manager["headers"],
        json={
            "name": "Updated Recycling Center",
            "description": "Updated center description",
            "processing_capacity_kg_per_day": 2000,
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["name"] == "Updated Recycling Center"
    assert data["description"] == "Updated center description"
    assert float(data["processing_capacity_kg_per_day"]) == 2000


def test_recycling_center_can_update_accepted_categories():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    new_category = create_waste_category(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=manager["headers"],
        json={
            "accepted_waste_category_ids": [
                new_category["id"]
            ]
        },
    )

    assert response.status_code == 200, response.text

    assert new_category["id"] in (
        response.json()["accepted_waste_category_ids"]
    )


def test_recycling_center_can_update_location():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)
    new_location = create_location(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=manager["headers"],
        json={
            "location_id": new_location["id"]
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["location_id"] == new_location["id"]


def test_recycling_center_update_rejects_duplicate_name():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    first = create_center(manager)
    second = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{second['id']}",
        headers=manager["headers"],
        json={
            "name": first["name"]
        },
    )

    assert response.status_code == 400
    assert "name already exists" in (
        response.json()["detail"].lower()
    )


def test_recycling_center_update_rejects_duplicate_code():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    first = create_center(manager)
    second = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{second['id']}",
        headers=manager["headers"],
        json={
            "code": first["code"]
        },
    )

    assert response.status_code == 400
    assert "code already exists" in (
        response.json()["detail"].lower()
    )


def test_customer_cannot_update_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)

    center = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=customer["headers"],
        json={
            "description": "Unauthorized update"
        },
    )

    assert response.status_code == 403


def test_empty_recycling_center_update_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=manager["headers"],
        json={},
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# RECYCLING CENTER STATUS TESTS
# ---------------------------------------------------------

def test_management_can_deactivate_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}/status",
        headers=manager["headers"],
        json={
            "status": "inactive"
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "inactive"
    assert response.json()["is_available"] is False


def test_management_can_activate_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(
        manager,
        is_available=False,
    )

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}/status",
        headers=manager["headers"],
        json={
            "status": "active"
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"
    assert response.json()["is_available"] is True


def test_management_can_mark_recycling_center_under_maintenance():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}/status",
        headers=manager["headers"],
        json={
            "status": "maintenance"
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "maintenance"
    assert response.json()["is_available"] is False


def test_management_can_set_center_availability():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}/status",
        headers=manager["headers"],
        json={
            "status": "active",
            "is_available": False,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "active"
    assert response.json()["is_available"] is False


def test_invalid_recycling_center_status_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    response = client.patch(
        f"/api/v1/recycling-centers/{center['id']}/status",
        headers=manager["headers"],
        json={
            "status": "unknown"
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# DELETE RECYCLING CENTER TESTS
# ---------------------------------------------------------

def test_management_can_delete_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    center = create_center(manager)

    response = client.delete(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=manager["headers"],
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=manager["headers"],
    )

    assert get_response.status_code == 404


def test_customer_cannot_delete_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)

    center = create_center(manager)

    response = client.delete(
        f"/api/v1/recycling-centers/{center['id']}",
        headers=customer["headers"],
    )

    assert response.status_code == 403


def test_deleting_nonexistent_recycling_center_returns_404():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    response = client.delete(
        f"/api/v1/recycling-centers/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404
