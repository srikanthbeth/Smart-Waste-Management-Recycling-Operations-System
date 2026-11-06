
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
from models.driver import Driver
from models.vehicle import Vehicle
from models.field_worker import FieldWorker

from core.constants import (
    UserRole,
    StaffStatus,
    StaffAvailability,
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


def unique_email():
    return f"assignment_{uuid4().hex[:10]}@example.com"


def register_user(role):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"Assignment {role.value}",
            "email": email,
            "password": "StrongPass123!",
            "phone_number": "9876543210",
        },
    )

    assert response.status_code in (200, 201), response.text

    db = TestingSessionLocal()

    try:
        user = db.query(User).filter(
            User.email == email
        ).first()

        assert user is not None

        user.role = role
        user.is_active = True
        user.is_verified = True

        db.commit()

        user_id = user.id

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
        "user_id": str(user_id),
        "token": token,
        "headers": {
            "Authorization": f"Bearer {token}"
        },
    }


def create_customer(manager=None):
    customer_user = register_user(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/customers",
        headers=customer_user["headers"],
        json={
            "customer_type": "residential",
            "property_type": "house",
            "service_address": "10 Test Street",
            "city": "Hyderabad",
            "state": "Telangana",
            "postal_code": "500001",
            "latitude": 17.385,
            "longitude": 78.4867,
            "monthly_waste_estimate_kg": 100,
            "notes": "Assignment test customer",
        },
    )

    assert response.status_code == 201, response.text

    return customer_user


def create_waste_category(manager):
    code = f"CAT-{uuid4().hex[:8].upper()}"

    response = client.post(
        "/api/v1/waste-categories",
        headers=manager["headers"],
        json={
            "name": f"Assignment Waste {uuid4().hex[:6]}",
            "code": code,
            "description": "Waste category for assignment tests",
            "is_recyclable": True,
            "is_hazardous": False,
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_pickup(manager, approve=True, quantity=25):
    customer = create_customer(manager)
    category = create_waste_category(manager)

    response = client.post(
        "/api/v1/pickups",
        headers=customer["headers"],
        json={
            "waste_category_id": category["id"],
            "estimated_quantity_kg": quantity,
            "preferred_date": (
                date.today() + timedelta(days=3)
            ).isoformat(),
            "preferred_time_slot": "Morning",
            "pickup_address": "10 Test Street",
            "city": "Hyderabad",
            "postal_code": "500001",
            "special_instructions": "Assignment test pickup",
        },
    )

    assert response.status_code == 201, response.text

    pickup = response.json()

    if approve:
        status_response = client.patch(
            f"/api/v1/pickups/{pickup['id']}/status",
            headers=manager["headers"],
            json={
                "status": "approved"
            },
        )

        assert status_response.status_code == 200, status_response.text

    return pickup


def create_driver(manager):
    driver_user = register_user(UserRole.DRIVER)

    response = client.post(
        "/api/v1/drivers",
        headers=manager["headers"],
        json={
            "user_id": driver_user["user_id"],
            "driver_code": f"DRV-{uuid4().hex[:8].upper()}",
            "license_number": f"LIC-{uuid4().hex[:10].upper()}",
            "license_type": "LMV",
            "license_expiry_date": (
                date.today() + timedelta(days=365)
            ).isoformat(),
            "phone": "9876543210",
            "address": "Hyderabad",
            "joining_date": date.today().isoformat(),
            "notes": "Assignment test driver",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_vehicle(manager, capacity=5000):
    response = client.post(
        "/api/v1/vehicles",
        headers=manager["headers"],
        json={
            "vehicle_code": f"VEH-{uuid4().hex[:8].upper()}",
            "registration_number": (
                f"TS{uuid4().hex[:2].upper()}"
                f"{uuid4().hex[:6].upper()}"
            ),
            "vehicle_type": "truck",
            "make": "Tata",
            "model": "407",
            "manufacturing_year": 2022,
            "fuel_type": "diesel",
            "capacity_kg": capacity,
            "current_odometer_km": 10000,
            "notes": "Assignment test vehicle",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_field_worker(manager):
    worker_user = register_user(UserRole.FIELD_WORKER)

    response = client.post(
        "/api/v1/field-workers",
        headers=manager["headers"],
        json={
            "user_id": worker_user["user_id"],
            "worker_code": f"WRK-{uuid4().hex[:8].upper()}",
            "phone": "9876543210",
            "address": "Hyderabad",
            "emergency_contact_name": "Test Contact",
            "emergency_contact_phone": "9876543211",
            "joining_date": date.today().isoformat(),
            "notes": "Assignment test worker",
        },
    )

    assert response.status_code == 201, response.text

    return response.json()


def create_scenario(
    approve=True,
    quantity=25,
    capacity=5000,
    with_worker=True,
):
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    pickup = create_pickup(
        manager,
        approve=approve,
        quantity=quantity,
    )

    driver = create_driver(manager)

    vehicle = create_vehicle(
        manager,
        capacity=capacity,
    )

    worker = (
        create_field_worker(manager)
        if with_worker
        else None
    )

    payload = {
        "pickup_id": pickup["id"],
        "driver_id": driver["id"],
        "vehicle_id": vehicle["id"],
        "scheduled_date": (
            date.today() + timedelta(days=3)
        ).isoformat(),
        "scheduled_time_slot": "Morning",
        "notes": "Test collection assignment",
    }

    if worker:
        payload["field_worker_ids"] = [worker["id"]]

    return {
        "manager": manager,
        "pickup": pickup,
        "driver": driver,
        "vehicle": vehicle,
        "worker": worker,
        "payload": payload,
    }


def create_assignment(scenario):
    response = client.post(
        "/api/v1/collection-assignments",
        headers=scenario["manager"]["headers"],
        json=scenario["payload"],
    )

    return response


def set_driver_availability(driver_id, availability):
    db = TestingSessionLocal()

    try:
        driver = db.query(Driver).filter(
            Driver.id == driver_id
        ).first()

        driver.availability = availability
        db.commit()

    finally:
        db.close()


def set_vehicle_status(vehicle_id, status):
    db = TestingSessionLocal()

    try:
        vehicle = db.query(Vehicle).filter(
            Vehicle.id == vehicle_id
        ).first()

        vehicle.status = status
        db.commit()

    finally:
        db.close()


def set_worker_availability(worker_id, availability):
    db = TestingSessionLocal()

    try:
        worker = db.query(FieldWorker).filter(
            FieldWorker.id == worker_id
        ).first()

        worker.availability = availability
        db.commit()

    finally:
        db.close()


def setup_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    collection_assignment_field_workers,
                    collection_assignments,
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
                    collection_assignment_field_workers,
                    collection_assignments,
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

    engine.dispose()


# ---------------------------------------------------------
# CREATE ASSIGNMENT TESTS
# ---------------------------------------------------------


def test_management_can_create_collection_assignment():
    scenario = create_scenario()

    response = create_assignment(scenario)

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["pickup_id"] == scenario["pickup"]["id"]
    assert data["driver_id"] == scenario["driver"]["id"]
    assert data["vehicle_id"] == scenario["vehicle"]["id"]
    assert data["status"] == "assigned"
    assert scenario["worker"]["id"] in data["field_worker_ids"]


def test_collection_assignment_requires_authentication():
    response = client.get(
        "/api/v1/collection-assignments"
    )

    assert response.status_code == 401


def test_customer_cannot_create_collection_assignment():
    scenario = create_scenario()

    customer = create_customer()

    response = client.post(
        "/api/v1/collection-assignments",
        headers=customer["headers"],
        json=scenario["payload"],
    )

    assert response.status_code == 403


def test_pickup_must_be_approved_or_scheduled():
    scenario = create_scenario(approve=False)

    response = create_assignment(scenario)

    assert response.status_code == 400
    assert "approved or scheduled" in response.json()["detail"]


def test_vehicle_capacity_must_be_sufficient():
    scenario = create_scenario(
        quantity=6000,
        capacity=5000,
    )

    response = create_assignment(scenario)

    assert response.status_code == 400
    assert "capacity" in response.json()["detail"].lower()


def test_driver_must_be_available():
    scenario = create_scenario()

    set_driver_availability(
        scenario["driver"]["id"],
        StaffAvailability.UNAVAILABLE,
    )

    response = create_assignment(scenario)

    assert response.status_code == 400
    assert "not available" in response.json()["detail"].lower()


def test_vehicle_must_be_available():
    scenario = create_scenario()

    set_vehicle_status(
        scenario["vehicle"]["id"],
        VehicleStatus.MAINTENANCE,
    )

    response = create_assignment(scenario)

    assert response.status_code == 400
    assert "not available" in response.json()["detail"].lower()


def test_field_worker_must_be_available():
    scenario = create_scenario()

    set_worker_availability(
        scenario["worker"]["id"],
        StaffAvailability.UNAVAILABLE,
    )

    response = create_assignment(scenario)

    assert response.status_code == 400
    assert "not available" in response.json()["detail"].lower()


def test_pickup_cannot_have_two_active_assignments():
    scenario = create_scenario()

    first_response = create_assignment(scenario)

    assert first_response.status_code == 201, first_response.text

    second_response = create_assignment(scenario)

    assert second_response.status_code == 400
    assert "active assignment" in second_response.json()["detail"].lower()


# ---------------------------------------------------------
# GET AND LIST ASSIGNMENT TESTS
# ---------------------------------------------------------


def test_management_can_get_collection_assignment():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    assignment_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/collection-assignments/{assignment_id}",
        headers=scenario["manager"]["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == assignment_id


def test_get_nonexistent_assignment_returns_404():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    response = client.get(
        f"/api/v1/collection-assignments/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404


def test_management_can_list_assignments():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    response = client.get(
        "/api/v1/collection-assignments",
        headers=scenario["manager"]["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_can_filter_assignments_by_pickup():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    response = client.get(
        "/api/v1/collection-assignments",
        headers=scenario["manager"]["headers"],
        params={
            "pickup_id": scenario["pickup"]["id"],
        },
    )

    assert response.status_code == 200
    assert all(
        item["pickup_id"] == scenario["pickup"]["id"]
        for item in response.json()
    )


def test_can_get_pickup_assignment_history():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    response = client.get(
        (
            "/api/v1/collection-assignments/"
            f"pickup/{scenario['pickup']['id']}/history"
        ),
        headers=scenario["manager"]["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# ---------------------------------------------------------
# UPDATE ASSIGNMENT TESTS
# ---------------------------------------------------------


def test_management_can_update_assignment_notes():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    assignment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/collection-assignments/{assignment_id}",
        headers=scenario["manager"]["headers"],
        json={
            "notes": "Updated collection instructions",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["notes"] == "Updated collection instructions"


def test_empty_assignment_update_rejected():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    assignment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/collection-assignments/{assignment_id}",
        headers=scenario["manager"]["headers"],
        json={},
    )

    assert response.status_code == 400


# ---------------------------------------------------------
# ASSIGNMENT STATUS TESTS
# ---------------------------------------------------------


def test_cannot_complete_assignment_without_starting():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    assignment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/collection-assignments/{assignment_id}/status",
        headers=scenario["manager"]["headers"],
        json={
            "status": "completed",
        },
    )

    assert response.status_code == 400


def test_cancellation_requires_reason():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    assignment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/collection-assignments/{assignment_id}/status",
        headers=scenario["manager"]["headers"],
        json={
            "status": "cancelled",
        },
    )

    assert response.status_code == 400
    assert "reason" in response.json()["detail"].lower()


def test_management_can_start_assignment():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    assignment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/collection-assignments/{assignment_id}/status",
        headers=scenario["manager"]["headers"],
        json={
            "status": "in_progress",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_progress"
    assert response.json()["started_at"] is not None


def test_management_can_complete_assignment():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    assignment_id = create_response.json()["id"]

    start_response = client.patch(
        f"/api/v1/collection-assignments/{assignment_id}/status",
        headers=scenario["manager"]["headers"],
        json={
            "status": "in_progress",
        },
    )

    assert start_response.status_code == 200, start_response.text

    complete_response = client.patch(
        f"/api/v1/collection-assignments/{assignment_id}/status",
        headers=scenario["manager"]["headers"],
        json={
            "status": "completed",
        },
    )

    assert complete_response.status_code == 200, complete_response.text
    assert complete_response.json()["status"] == "completed"
    assert complete_response.json()["completed_at"] is not None


def test_management_can_cancel_assignment():
    scenario = create_scenario()

    create_response = create_assignment(scenario)

    assert create_response.status_code == 201, create_response.text

    assignment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/collection-assignments/{assignment_id}/status",
        headers=scenario["manager"]["headers"],
        json={
            "status": "cancelled",
            "cancellation_reason": "Vehicle breakdown",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancellation_reason"] == "Vehicle breakdown"
