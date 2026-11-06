
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

from core.constants import (
    UserRole,
    PickupStatus,
    VehicleStatus,
)

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
    return f"transfer_{uuid4().hex[:10]}@example.com"


def register_user(role):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"Transfer {role.value}",
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
            "name": f"Transfer Zone {uuid4().hex[:6]}",
            "code": f"TZ-{uuid4().hex[:8].upper()}",
            "location_type": "zone",
            "description": "Waste transfer test zone",
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
            "name": f"Transfer Waste {uuid4().hex[:6]}",
            "code": f"TW-{uuid4().hex[:8].upper()}",
            "description": "Transfer test waste category",
            "is_recyclable": True,
            "is_hazardous": False,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()

def create_customer(manager, location):
    customer_user = register_user(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/customers",
        headers={
            "Authorization": f"Bearer {customer_user['token']}"
        },
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
            "notes": "Waste transfer test customer",
        },
    )

    assert response.status_code == 201, response.text

    customer_profile = response.json()

    customer_profile["headers"] = {
        "Authorization": f"Bearer {customer_user['token']}"
    }

    return customer_profile


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
            "special_instructions": "Waste transfer test pickup",
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
        headers={
            "Authorization": f"Bearer {manager['token']}"
        },
        json={
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
            "notes": "Waste transfer test vehicle",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()

def create_center(manager, location, category):
    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json={
            "name": f"Transfer Center {uuid4().hex[:8]}",
            "code": f"TC-{uuid4().hex[:8].upper()}",
            "description": "Waste transfer test center",
            "location_id": location["id"],
            "manager_user_id": manager["user_id"],
            "processing_capacity_kg_per_day": 1000,
            "is_available": True,
            "accepted_waste_category_ids": [category["id"]],
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_transfer_payload(manager):
    location = create_location(manager)
    category = create_category(manager)
    customer = create_customer(manager, location)
    pickup = create_pickup(manager, customer, category, location)
    vehicle = create_vehicle(manager)
    center = create_center(manager, location, category)

    return {
        "pickup_id": pickup["id"],
        "source_location_id": location["id"],
        "recycling_center_id": center["id"],
        "waste_category_id": category["id"],
        "vehicle_id": vehicle["id"],
        "quantity_kg": 40,
        "remarks": "Test waste transfer",
    }


def create_transfer(manager):
    payload = create_transfer_payload(manager)

    response = client.post(
        "/api/v1/waste-transfers",
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

def test_operations_manager_can_create_transfer():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    payload = create_transfer_payload(manager)

    response = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["pickup_id"] == payload["pickup_id"]
    assert data["recycling_center_id"] == payload["recycling_center_id"]
    assert data["waste_category_id"] == payload["waste_category_id"]
    assert float(data["quantity_kg"]) == 40
    assert data["status"] == "pending"
    assert data["transfer_number"].startswith("WT-")


def test_super_admin_can_create_transfer():
    admin = register_user(UserRole.SUPER_ADMIN)
    payload = create_transfer_payload(admin)

    response = client.post(
        "/api/v1/waste-transfers",
        headers=admin["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text


def test_transfer_requires_authentication():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    payload = create_transfer_payload(manager)

    response = client.post(
        "/api/v1/waste-transfers",
        json=payload,
    )

    assert response.status_code == 401


def test_customer_cannot_create_transfer():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)
    payload = create_transfer_payload(manager)

    response = client.post(
        "/api/v1/waste-transfers",
        headers=customer["headers"],
        json=payload,
    )

    assert response.status_code == 403


def test_transfer_rejects_non_completed_pickup():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    payload = create_transfer_payload(manager)

    db = TestingSessionLocal()

    try:
        pickup = db.get(Pickup, payload["pickup_id"])
        pickup.status = PickupStatus.ASSIGNED
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 400
    assert "completed pickups" in response.json()["detail"].lower()


def test_transfer_rejects_nonexistent_pickup():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    payload = create_transfer_payload(manager)
    payload["pickup_id"] = str(uuid4())

    response = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 404


def test_transfer_rejects_nonexistent_recycling_center():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    payload = create_transfer_payload(manager)
    payload["recycling_center_id"] = str(uuid4())

    response = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 404


def test_transfer_rejects_nonexistent_vehicle():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    payload = create_transfer_payload(manager)
    payload["vehicle_id"] = str(uuid4())

    response = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 404


def test_transfer_quantity_must_be_positive():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    payload = create_transfer_payload(manager)
    payload["quantity_kg"] = 0

    response = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 422


def test_duplicate_transfer_for_pickup_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    payload = create_transfer_payload(manager)

    first = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json=payload,
    )

    assert second.status_code == 400
    assert "already exists" in second.json()["detail"].lower()


# ---------------------------------------------------------
# GET AND LIST TESTS
# ---------------------------------------------------------

def test_management_can_get_transfer():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    response = client.get(
        f"/api/v1/waste-transfers/{transfer['id']}",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == transfer["id"]


def test_nonexistent_transfer_returns_404():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    response = client.get(
        f"/api/v1/waste-transfers/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404


def test_management_can_list_transfers():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    create_transfer(manager)
    create_transfer(manager)

    response = client.get(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_customer_cannot_list_transfers():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)

    create_transfer(manager)

    response = client.get(
        "/api/v1/waste-transfers",
        headers=customer["headers"],
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# UPDATE TESTS
# ---------------------------------------------------------

def test_management_can_update_pending_transfer():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    response = client.patch(
        f"/api/v1/waste-transfers/{transfer['id']}",
        headers=manager["headers"],
        json={
            "quantity_kg": 35,
            "remarks": "Updated transfer quantity",
        },
    )

    assert response.status_code == 200, response.text
    assert float(response.json()["quantity_kg"]) == 35


def test_empty_transfer_update_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    response = client.patch(
        f"/api/v1/waste-transfers/{transfer['id']}",
        headers=manager["headers"],
        json={},
    )

    assert response.status_code == 422


def test_customer_cannot_update_transfer():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)
    transfer = create_transfer(manager)

    response = client.patch(
        f"/api/v1/waste-transfers/{transfer['id']}",
        headers=customer["headers"],
        json={"remarks": "Unauthorized update"},
    )

    assert response.status_code == 403


# ---------------------------------------------------------
# DISPATCH AND TRANSIT TESTS
# ---------------------------------------------------------

def test_management_can_dispatch_transfer():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={"remarks": "Vehicle dispatched"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "dispatched"
    assert response.json()["dispatched_at"] is not None


def test_pending_transfer_can_be_marked_in_transit():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    dispatch = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )

    assert dispatch.status_code == 200, dispatch.text

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/in-transit",
        headers=manager["headers"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_transit"


def test_pending_transfer_cannot_be_marked_in_transit_directly():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/in-transit",
        headers=manager["headers"],
    )

    assert response.status_code == 400


# ---------------------------------------------------------
# RECEIVE TESTS
# ---------------------------------------------------------

def test_transfer_can_be_fully_received():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/in-transit",
        headers=manager["headers"],
    )

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/receive",
        headers=manager["headers"],
        json={"received_quantity_kg": 40},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "received"
    assert float(response.json()["received_quantity_kg"]) == 40
    assert response.json()["received_by_user_id"] == manager["user_id"]


def test_transfer_can_be_partially_received():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/in-transit",
        headers=manager["headers"],
    )

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/receive",
        headers=manager["headers"],
        json={"received_quantity_kg": 30},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "partially_received"
    assert float(response.json()["received_quantity_kg"]) == 30


def test_received_quantity_cannot_exceed_dispatched_quantity():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/in-transit",
        headers=manager["headers"],
    )

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/receive",
        headers=manager["headers"],
        json={"received_quantity_kg": 45},
    )

    assert response.status_code == 400
    assert "cannot exceed" in response.json()["detail"].lower()


def test_transfer_cannot_be_received_before_transit():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/receive",
        headers=manager["headers"],
        json={"received_quantity_kg": 20},
    )

    assert response.status_code == 400


# ---------------------------------------------------------
# REJECT AND CANCEL TESTS
# ---------------------------------------------------------

def test_dispatched_transfer_can_be_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/reject",
        headers=manager["headers"],
        json={"remarks": "Rejected by receiving center"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rejected"


def test_rejection_requires_remarks():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/reject",
        headers=manager["headers"],
        json={},
    )

    assert response.status_code == 400


def test_pending_transfer_can_be_cancelled():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/cancel",
        headers=manager["headers"],
        json={"remarks": "Cancelled for testing"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"


def test_received_transfer_cannot_be_cancelled():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    transfer = create_transfer(manager)

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )

    client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/in-transit",
        headers=manager["headers"],
    )

    receive = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/receive",
        headers=manager["headers"],
        json={"received_quantity_kg": 40},
    )

    assert receive.status_code == 200, receive.text

    response = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/cancel",
        headers=manager["headers"],
        json={},
    )

    assert response.status_code == 400
