
import os
from datetime import date, timedelta
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
from models.pickup import Pickup
from core.constants import UserRole, PickupStatus


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
    return f"segregation_{uuid4().hex[:10]}@example.com"


def register_user(role):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"Segregation {role.value}",
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

    assert login_response.status_code == 200, login_response.text

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
            "name": f"Segregation Zone {uuid4().hex[:6]}",
            "code": f"SZ-{uuid4().hex[:8].upper()}",
            "location_type": "zone",
            "description": "Segregation test zone",
            "city": "Hyderabad",
            "state": "Telangana",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_category(manager):
    response = client.post(
        "/api/v1/waste-categories",
        headers=manager["headers"],
        json={
            "name": f"Segregation Waste {uuid4().hex[:6]}",
            "code": f"SW-{uuid4().hex[:8].upper()}",
            "description": "Segregation test category",
            "is_recyclable": True,
            "is_hazardous": False,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_customer(manager):
    customer_user = register_user(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/customers",
        headers=customer_user["headers"],
        json={
            "customer_type": "residential",
            "property_type": "house",
            "service_address": "12 Green Street",
            "city": "Hyderabad",
            "state": "Telangana",
            "postal_code": "500001",
            "latitude": 17.3850,
            "longitude": 78.4867,
            "monthly_waste_estimate_kg": 25,
            "notes": "Segregation test customer",
        },
    )

    assert response.status_code == 201, response.text

    customer = response.json()
    customer["headers"] = customer_user["headers"]

    return customer


def create_pickup(manager, customer, category, location):
    response = client.post(
        "/api/v1/pickups",
        headers=customer["headers"],
        json={
            "waste_category_id": category["id"],
            "location_id": location["id"],
            "estimated_quantity_kg": 50,
            "preferred_date": (
                date.today() + timedelta(days=5)
            ).isoformat(),
            "preferred_time_slot": "Morning",
            "pickup_address": "12 Green Street",
            "city": "Hyderabad",
            "postal_code": "500001",
            "special_instructions": "Segregation test pickup",
        },
    )

    assert response.status_code == 201, response.text

    pickup = response.json()

    with TestingSessionLocal() as db:
        db_pickup = db.get(Pickup, pickup["id"])
        assert db_pickup is not None

        db_pickup.status = PickupStatus.COMPLETED
        db.commit()

    return pickup


def create_vehicle(manager):
    unique = uuid4().hex[:8].upper()

    response = client.post(
        "/api/v1/vehicles",
        headers=manager["headers"],
        json={
            "vehicle_code": f"SEG-VEH-{unique}",
            "registration_number": f"TS09{unique[:6]}",
            "vehicle_type": "truck",
            "make": "Tata",
            "model": "407",
            "manufacturing_year": date.today().year - 2,
            "fuel_type": "diesel",
            "capacity_kg": 5000,
            "current_odometer_km": 25000,
            "location_id": None,
            "notes": "Segregation test vehicle",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_center(manager, location, category):
    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json={
            "name": f"Segregation Center {uuid4().hex[:8]}",
            "code": f"SC-{uuid4().hex[:8].upper()}",
            "description": "Segregation test center",
            "location_id": location["id"],
            "manager_user_id": manager["user_id"],
            "processing_capacity_kg_per_day": 1000,
            "is_available": True,
            "accepted_waste_category_ids": [category["id"]],
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_transfer(manager):
    location = create_location(manager)
    category = create_category(manager)
    customer = create_customer(manager)
    pickup = create_pickup(
        manager, customer, category, location
    )
    vehicle = create_vehicle(manager)
    center = create_center(manager, location, category)

    payload = {
        "pickup_id": pickup["id"],
        "source_location_id": location["id"],
        "recycling_center_id": center["id"],
        "waste_category_id": category["id"],
        "vehicle_id": vehicle["id"],
        "quantity_kg": 40,
        "remarks": "Segregation test transfer",
    }

    response = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text
    transfer = response.json()

    # Dispatch transfer.
    dispatch = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )
    assert dispatch.status_code == 200, dispatch.text

    # Mark transfer in transit.
    transit = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/in-transit",
        headers=manager["headers"],
    )
    assert transit.status_code == 200, transit.text

    # Receive all transferred waste.
    receive = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/receive",
        headers=manager["headers"],
        json={"received_quantity_kg": 40},
    )
    assert receive.status_code == 200, receive.text

    return {
        "transfer": receive.json(),
        "center": center,
        "category": category,
        "location": location,
    }


def create_segregation_payload(manager):
    data = create_transfer(manager)

    payload = {
        "transfer_id": data["transfer"]["id"],
        "incoming_quantity_kg": 40,
        "recyclable_quantity_kg": 25,
        "non_recyclable_quantity_kg": 10,
        "contaminated_quantity_kg": 5,
        "remarks": "Waste segregated successfully",
    }

    return data, payload


def create_segregation(manager):
    data, payload = create_segregation_payload(manager)

    response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text

    return response.json(), data


def setup_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    waste_segregations,
                    waste_transfers,
                    collection_trackings,
                    collection_assignments,
                    recycling_center_waste_categories,
                    recycling_centers,
                    vehicles,
                    pickups,
                    customers,
                    waste_categories,
                    locations,
                    field_workers,
                    drivers,
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
                    waste_segregations,
                    waste_transfers,
                    collection_trackings,
                    collection_assignments,
                    recycling_center_waste_categories,
                    recycling_centers,
                    vehicles,
                    pickups,
                    customers,
                    waste_categories,
                    locations,
                    field_workers,
                    drivers,
                    password_reset_tokens,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )

    engine.dispose()


# ---------------------------------------------------------
# CREATE TESTS
# ---------------------------------------------------------

def test_operations_manager_can_create_segregation():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    data, payload = create_segregation_payload(manager)

    response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text

    result = response.json()

    assert result["transfer_id"] == payload["transfer_id"]
    assert result["recycling_center_id"] == data["center"]["id"]
    assert result["waste_category_id"] == data["category"]["id"]
    assert float(result["incoming_quantity_kg"]) == 40
    assert float(result["recyclable_quantity_kg"]) == 25
    assert float(result["non_recyclable_quantity_kg"]) == 10
    assert float(result["contaminated_quantity_kg"]) == 5
    assert result["status"] == "completed"
    assert result["segregated_by_user_id"] == manager["user_id"]


def test_super_admin_can_create_segregation():
    admin = register_user(UserRole.SUPER_ADMIN)
    data, payload = create_segregation_payload(admin)

    response = client.post(
        "/api/v1/waste-segregations",
        headers=admin["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text


def test_segregation_requires_authentication():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_segregation_payload(manager)

    response = client.post(
        "/api/v1/waste-segregations",
        json=payload,
    )

    assert response.status_code == 401


def test_customer_cannot_create_segregation():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)
    _, payload = create_segregation_payload(manager)

    response = client.post(
        "/api/v1/waste-segregations",
        headers=customer["headers"],
        json=payload,
    )

    assert response.status_code == 403


def test_segregation_rejects_nonexistent_transfer():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_segregation_payload(manager)

    payload["transfer_id"] = str(uuid4())

    response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 404


def test_incoming_quantity_must_be_positive():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_segregation_payload(manager)

    payload["incoming_quantity_kg"] = 0

    response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 422


def test_negative_recyclable_quantity_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_segregation_payload(manager)

    payload["recyclable_quantity_kg"] = -5

    response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 422


def test_segregated_quantity_cannot_exceed_incoming_quantity():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_segregation_payload(manager)

    payload["recyclable_quantity_kg"] = 30
    payload["non_recyclable_quantity_kg"] = 15
    payload["contaminated_quantity_kg"] = 5

    response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 422


def test_partially_segregated_waste_is_recorded():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_segregation_payload(manager)

    payload["recyclable_quantity_kg"] = 20
    payload["non_recyclable_quantity_kg"] = 10
    payload["contaminated_quantity_kg"] = 5

    response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "partially_segregated"


def test_transfer_cannot_be_segregated_beyond_received_quantity():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    data, payload = create_segregation_payload(manager)

    payload["incoming_quantity_kg"] = 41

    response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 400


def test_transfer_quantity_cannot_be_recorded_twice():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    data, payload = create_segregation_payload(manager)

    first = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=payload,
    )

    assert first.status_code == 201, first.text

    second_payload = payload.copy()
    second_payload["incoming_quantity_kg"] = 1
    second_payload["recyclable_quantity_kg"] = 1
    second_payload["non_recyclable_quantity_kg"] = 0
    second_payload["contaminated_quantity_kg"] = 0

    second = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json=second_payload,
    )

    assert second.status_code == 400


# ---------------------------------------------------------
# GET AND LIST TESTS
# ---------------------------------------------------------

def test_management_can_get_segregation():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    segregation, _ = create_segregation(manager)

    response = client.get(
        f"/api/v1/waste-segregations/{segregation['id']}",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == segregation["id"]


def test_nonexistent_segregation_returns_404():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    response = client.get(
        f"/api/v1/waste-segregations/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404


def test_management_can_list_segregations():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    create_segregation(manager)
    create_segregation(manager)

    response = client.get(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_customer_cannot_list_segregations():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)

    create_segregation(manager)

    response = client.get(
        "/api/v1/waste-segregations",
        headers=customer["headers"],
    )

    assert response.status_code == 403


def test_management_can_view_transfer_segregation_history():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    segregation, data = create_segregation(manager)

    response = client.get(
        (
            "/api/v1/waste-segregations/transfer/"
            f"{data['transfer']['id']}/history"
        ),
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1
    assert response.json()[0]["id"] == segregation["id"]


# ---------------------------------------------------------
# UPDATE TESTS
# ---------------------------------------------------------

def test_management_can_update_segregation():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    segregation, _ = create_segregation(manager)

    response = client.patch(
        f"/api/v1/waste-segregations/{segregation['id']}",
        headers=manager["headers"],
        json={
            "recyclable_quantity_kg": 20,
            "non_recyclable_quantity_kg": 15,
            "contaminated_quantity_kg": 5,
            "remarks": "Updated segregation quantities",
        },
    )

    assert response.status_code == 200, response.text

    result = response.json()

    assert float(result["recyclable_quantity_kg"]) == 20
    assert float(result["non_recyclable_quantity_kg"]) == 15
    assert result["status"] == "completed"


def test_empty_segregation_update_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    segregation, _ = create_segregation(manager)

    response = client.patch(
        f"/api/v1/waste-segregations/{segregation['id']}",
        headers=manager["headers"],
        json={},
    )

    assert response.status_code == 422


def test_customer_cannot_update_segregation():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)
    segregation, _ = create_segregation(manager)

    response = client.patch(
        f"/api/v1/waste-segregations/{segregation['id']}",
        headers=customer["headers"],
        json={"remarks": "Unauthorized update"},
    )

    assert response.status_code == 403


def test_segregation_update_rejects_quantity_above_incoming():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    segregation, _ = create_segregation(manager)

    response = client.patch(
        f"/api/v1/waste-segregations/{segregation['id']}",
        headers=manager["headers"],
        json={
            "recyclable_quantity_kg": 30,
            "non_recyclable_quantity_kg": 20,
            "contaminated_quantity_kg": 5,
        },
    )

    assert response.status_code == 400
    assert "exceed" in response.json()["detail"].lower()