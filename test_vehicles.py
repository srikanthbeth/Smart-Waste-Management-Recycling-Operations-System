
import os
from uuid import uuid4
from datetime import date

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:Srik8499@localhost:5433/smart_waste_management_test",
)

from fastapi.testclient import TestClient
from sqlalchemy import text

from db.session import SessionLocal, engine
from main import app
from models.user import User
from core.constants import UserRole


client = TestClient(app)

PASSWORD = "StrongPassword123!"


def setup_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
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


def unique_email():
    return f"vehicle_test_{uuid4().hex[:10]}@example.com"


def register_user(role=UserRole.CUSTOMER):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Vehicle Test User",
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 201, response.text

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None

        user.role = role
        db.commit()
    finally:
        db.close()

    return email


def login_user(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def create_user_with_role(role):
    email = register_user(role)
    headers = login_user(email)
    return email, headers


def vehicle_payload():
    unique = uuid4().hex[:8].upper()

    return {
        "vehicle_code": f"VEH-{unique}",
        "registration_number": f"TS09{unique[:6]}",
        "vehicle_type": "truck",
        "make": "Tata",
        "model": "407",
        "manufacturing_year": date.today().year - 2,
        "fuel_type": "diesel",
        "capacity_kg": 5000,
        "current_odometer_km": 25000,
        "location_id": None,
        "notes": "Waste collection vehicle",
    }


def create_vehicle(headers, payload=None):
    if payload is None:
        payload = vehicle_payload()

    return client.post(
        "/api/v1/vehicles",
        json=payload,
        headers=headers,
    )


# ---------------------------------------------------------
# CREATE VEHICLE TESTS
# ---------------------------------------------------------


def test_operations_manager_can_create_vehicle():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    response = create_vehicle(headers)

    assert response.status_code == 201, response.text
    data = response.json()

    assert data["vehicle_code"].startswith("VEH-")
    assert data["registration_number"]
    assert data["vehicle_type"] == "truck"
    assert data["make"] == "Tata"
    assert data["model"] == "407"
    assert data["fuel_type"] == "diesel"
    assert float(data["capacity_kg"]) == 5000
    assert data["status"] == "available"
    assert data["is_active"] is True


def test_super_admin_can_create_vehicle():
    _, headers = create_user_with_role(
        UserRole.SUPER_ADMIN
    )

    response = create_vehicle(headers)

    assert response.status_code == 201, response.text


def test_collection_supervisor_can_create_vehicle():
    _, headers = create_user_with_role(
        UserRole.COLLECTION_SUPERVISOR
    )

    response = create_vehicle(headers)

    assert response.status_code == 201, response.text


def test_vehicle_creation_requires_authentication():
    response = client.post(
        "/api/v1/vehicles",
        json=vehicle_payload(),
    )

    assert response.status_code == 401


def test_customer_cannot_create_vehicle():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_vehicle(headers)

    assert response.status_code == 403


def test_driver_cannot_create_vehicle():
    _, headers = create_user_with_role(
        UserRole.DRIVER
    )

    response = create_vehicle(headers)

    assert response.status_code == 403


def test_vehicle_code_is_normalized():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    payload["vehicle_code"] = "  vehicle-abc123  "

    response = create_vehicle(headers, payload)

    assert response.status_code == 201, response.text
    assert response.json()["vehicle_code"] == "VEHICLE-ABC123"


def test_duplicate_vehicle_code_rejected():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()

    first = create_vehicle(headers, payload)
    assert first.status_code == 201, first.text

    second_payload = vehicle_payload()
    second_payload["vehicle_code"] = payload["vehicle_code"]

    response = create_vehicle(headers, second_payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Vehicle code already exists"


def test_duplicate_registration_number_rejected():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()

    first = create_vehicle(headers, payload)
    assert first.status_code == 201, first.text

    second_payload = vehicle_payload()
    second_payload["registration_number"] = payload[
        "registration_number"
    ]

    response = create_vehicle(headers, second_payload)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Vehicle registration number already exists"
    )


def test_vehicle_requires_vehicle_code():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    del payload["vehicle_code"]

    response = create_vehicle(headers, payload)

    assert response.status_code == 422


def test_vehicle_requires_registration_number():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    del payload["registration_number"]

    response = create_vehicle(headers, payload)

    assert response.status_code == 422


def test_vehicle_rejects_zero_capacity():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    payload["capacity_kg"] = 0

    response = create_vehicle(headers, payload)

    assert response.status_code == 422


def test_vehicle_rejects_negative_capacity():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    payload["capacity_kg"] = -100

    response = create_vehicle(headers, payload)

    assert response.status_code == 422


def test_vehicle_rejects_negative_odometer():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    payload["current_odometer_km"] = -10

    response = create_vehicle(headers, payload)

    assert response.status_code == 422


def test_vehicle_rejects_invalid_vehicle_type():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    payload["vehicle_type"] = "airplane"

    response = create_vehicle(headers, payload)

    assert response.status_code == 422


def test_vehicle_rejects_invalid_fuel_type():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    payload["fuel_type"] = "nuclear"

    response = create_vehicle(headers, payload)

    assert response.status_code == 422


def test_vehicle_rejects_invalid_manufacturing_year():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    payload["manufacturing_year"] = 1970

    response = create_vehicle(headers, payload)

    assert response.status_code == 422


def test_vehicle_rejects_nonexistent_location():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()
    payload["location_id"] = str(uuid4())

    response = create_vehicle(headers, payload)

    assert response.status_code == 404


# ---------------------------------------------------------
# LIST VEHICLE TESTS
# ---------------------------------------------------------


def test_operations_manager_can_list_vehicles():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.get(
        "/api/v1/vehicles",
        headers=headers,
    )

    assert response.status_code == 200

    vehicle_ids = [
        vehicle["id"] for vehicle in response.json()
    ]

    assert vehicle_id in vehicle_ids


def test_collection_supervisor_can_list_vehicles():
    _, headers = create_user_with_role(
        UserRole.COLLECTION_SUPERVISOR
    )

    response = client.get(
        "/api/v1/vehicles",
        headers=headers,
    )

    assert response.status_code == 200


def test_customer_cannot_list_vehicles():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = client.get(
        "/api/v1/vehicles",
        headers=headers,
    )

    assert response.status_code == 403


def test_vehicle_list_requires_authentication():
    response = client.get("/api/v1/vehicles")

    assert response.status_code == 401


def test_vehicle_list_can_filter_by_status():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = vehicle_payload()

    created = create_vehicle(headers, payload)
    assert created.status_code == 201, created.text

    response = client.get(
        "/api/v1/vehicles?status=available",
        headers=headers,
    )

    assert response.status_code == 200

    assert all(
        vehicle["status"] == "available"
        for vehicle in response.json()
    )


def test_vehicle_list_can_filter_by_type():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    response = client.get(
        "/api/v1/vehicles?vehicle_type=truck",
        headers=headers,
    )

    assert response.status_code == 200

    assert all(
        vehicle["vehicle_type"] == "truck"
        for vehicle in response.json()
    )


# ---------------------------------------------------------
# GET VEHICLE TESTS
# ---------------------------------------------------------


def test_operations_manager_can_get_vehicle():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.get(
        f"/api/v1/vehicles/{vehicle_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == vehicle_id


def test_get_nonexistent_vehicle():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    response = client.get(
        f"/api/v1/vehicles/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


def test_get_vehicle_requires_authentication():
    response = client.get(
        f"/api/v1/vehicles/{uuid4()}"
    )

    assert response.status_code == 401


# ---------------------------------------------------------
# UPDATE VEHICLE TESTS
# ---------------------------------------------------------


def test_operations_manager_can_update_vehicle():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}",
        json={
            "make": "Ashok Leyland",
            "model": "Partner",
            "capacity_kg": 6000,
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["make"] == "Ashok Leyland"
    assert response.json()["model"] == "Partner"
    assert float(response.json()["capacity_kg"]) == 6000


def test_update_vehicle_rejects_empty_payload():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}",
        json={},
        headers=headers,
    )

    assert response.status_code == 400


def test_update_vehicle_rejects_duplicate_code():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    first = create_vehicle(headers)
    second = create_vehicle(headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    second_id = second.json()["id"]
    first_code = first.json()["vehicle_code"]

    response = client.patch(
        f"/api/v1/vehicles/{second_id}",
        json={"vehicle_code": first_code},
        headers=headers,
    )

    assert response.status_code == 409


def test_update_vehicle_rejects_duplicate_registration():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    first = create_vehicle(headers)
    second = create_vehicle(headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    second_id = second.json()["id"]
    first_registration = first.json()["registration_number"]

    response = client.patch(
        f"/api/v1/vehicles/{second_id}",
        json={
            "registration_number": first_registration
        },
        headers=headers,
    )

    assert response.status_code == 409


def test_customer_cannot_update_vehicle():
    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )
    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    created = create_vehicle(manager_headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}",
        json={"make": "Updated Make"},
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_update_nonexistent_vehicle():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    response = client.patch(
        f"/api/v1/vehicles/{uuid4()}",
        json={"make": "Updated Make"},
        headers=headers,
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# VEHICLE STATUS TESTS
# ---------------------------------------------------------


def test_operations_manager_can_update_vehicle_status():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "maintenance"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "maintenance"


def test_vehicle_can_be_marked_out_of_service():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "out_of_service"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "out_of_service"


def test_vehicle_can_be_retired():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "retired"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "retired"
    assert response.json()["is_active"] is False


def test_retired_vehicle_cannot_be_updated():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    retired = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "retired"},
        headers=headers,
    )

    assert retired.status_code == 200, retired.text

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}",
        json={"make": "Updated Make"},
        headers=headers,
    )

    assert response.status_code == 400


def test_retired_vehicle_cannot_change_status():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    retired = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "retired"},
        headers=headers,
    )

    assert retired.status_code == 200, retired.text

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "available"},
        headers=headers,
    )

    assert response.status_code == 400


def test_vehicle_status_rejects_invalid_value():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    created = create_vehicle(headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "broken"},
        headers=headers,
    )

    assert response.status_code == 422


def test_customer_cannot_update_vehicle_status():
    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )
    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    created = create_vehicle(manager_headers)
    assert created.status_code == 201, created.text

    vehicle_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/vehicles/{vehicle_id}/status",
        json={"status": "maintenance"},
        headers=customer_headers,
    )

    assert response.status_code == 403
