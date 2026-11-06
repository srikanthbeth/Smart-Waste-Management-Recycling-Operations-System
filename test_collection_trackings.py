
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
from models.collection_assignment import CollectionAssignment
from models.collection_tracking import CollectionTracking

from core.constants import (
    UserRole,
    AssignmentStatus,
    StaffAvailability,
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
    return f"tracking_{uuid4().hex[:10]}@example.com"


def register_user(role):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"Tracking {role.value}",
            "email": email,
            "password": "StrongPass123!",
            "phone_number": "9876543210",
        },
    )

    assert response.status_code in (200, 201), response.text

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
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


def create_customer(manager):
    customer = register_user(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/customers",
        headers=customer["headers"],
        json={
            "customer_type": "residential",
            "property_type": "house",
            "service_address": "10 Tracking Test Street",
            "city": "Hyderabad",
            "state": "Telangana",
            "postal_code": "500001",
            "latitude": 17.385,
            "longitude": 78.4867,
            "monthly_waste_estimate_kg": 100,
            "notes": "Tracking test customer",
        },
    )

    assert response.status_code == 201, response.text
    return customer


def create_waste_category(manager):
    response = client.post(
        "/api/v1/waste-categories",
        headers=manager["headers"],
        json={
            "name": f"Tracking Waste {uuid4().hex[:6]}",
            "code": f"CAT-{uuid4().hex[:8].upper()}",
            "description": "Tracking test category",
            "is_recyclable": True,
            "is_hazardous": False,
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_pickup(manager, quantity=25):
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
            "pickup_address": "10 Tracking Test Street",
            "city": "Hyderabad",
            "postal_code": "500001",
            "special_instructions": "Tracking test pickup",
        },
    )

    assert response.status_code == 201, response.text
    pickup = response.json()

    approval = client.patch(
        f"/api/v1/pickups/{pickup['id']}/status",
        headers=manager["headers"],
        json={"status": "approved"},
    )

    assert approval.status_code == 200, approval.text
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
            "notes": "Tracking test driver",
        },
    )

    assert response.status_code == 201, response.text

    return {
        "profile": response.json(),
        "user": driver_user,
    }


def create_vehicle(manager, capacity=5000):
    response = client.post(
        "/api/v1/vehicles",
        headers=manager["headers"],
        json={
            "vehicle_code": f"VEH-{uuid4().hex[:8].upper()}",
            "registration_number": f"TS{uuid4().hex[:8].upper()}",
            "vehicle_type": "truck",
            "make": "Tata",
            "model": "407",
            "manufacturing_year": 2022,
            "fuel_type": "diesel",
            "capacity_kg": capacity,
            "current_odometer_km": 10000,
            "notes": "Tracking test vehicle",
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
            "notes": "Tracking test worker",
        },
    )

    assert response.status_code == 201, response.text

    return {
        "profile": response.json(),
        "user": worker_user,
    }


def create_scenario(quantity=25, capacity=5000, with_worker=True):
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    pickup = create_pickup(manager, quantity)

    driver = create_driver(manager)
    vehicle = create_vehicle(manager, capacity)

    worker = (
        create_field_worker(manager)
        if with_worker
        else None
    )

    assignment_payload = {
        "pickup_id": pickup["id"],
        "driver_id": driver["profile"]["id"],
        "vehicle_id": vehicle["id"],
        "scheduled_date": (
            date.today() + timedelta(days=3)
        ).isoformat(),
        "scheduled_time_slot": "Morning",
        "notes": "Tracking assignment",
    }

    if worker:
        assignment_payload["field_worker_ids"] = [
            worker["profile"]["id"]
        ]

    assignment_response = client.post(
        "/api/v1/collection-assignments",
        headers=manager["headers"],
        json=assignment_payload,
    )

    assert assignment_response.status_code == 201, (
        assignment_response.text
    )

    return {
        "manager": manager,
        "pickup": pickup,
        "driver": driver,
        "vehicle": vehicle,
        "worker": worker,
        "assignment": assignment_response.json(),
    }


def start_tracking(scenario, staff=None):
    if staff is None:
        staff = scenario["driver"]["user"]

    return client.post(
        "/api/v1/collection-trackings",
        headers=staff["headers"],
        json={
            "assignment_id": scenario["assignment"]["id"],
            "remarks": "Collection started",
            "photo_urls": [
                "https://example.com/collection-start.jpg"
            ],
        },
    )


def setup_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    collection_trackings,
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
                    collection_trackings,
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
# START TRACKING TESTS
# ---------------------------------------------------------

def test_assigned_driver_can_start_tracking():
    scenario = create_scenario()

    response = start_tracking(scenario)

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "in_progress"
    assert response.json()["assignment_id"] == scenario["assignment"]["id"]
    assert response.json()["pickup_id"] == scenario["pickup"]["id"]


def test_assigned_field_worker_can_start_tracking():
    scenario = create_scenario()

    response = start_tracking(
        scenario,
        scenario["worker"]["user"],
    )

    assert response.status_code == 201, response.text


def test_tracking_requires_authentication():
    scenario = create_scenario()

    response = client.post(
        "/api/v1/collection-trackings",
        json={
            "assignment_id": scenario["assignment"]["id"]
        },
    )

    assert response.status_code == 401


def test_customer_cannot_start_tracking():
    scenario = create_scenario()
    customer = register_user(UserRole.CUSTOMER)

    response = start_tracking(scenario, customer)

    assert response.status_code == 403


def test_unassigned_driver_cannot_start_tracking():
    scenario = create_scenario()
    another_driver = register_user(UserRole.DRIVER)

    response = start_tracking(scenario, another_driver)

    assert response.status_code == 403


def test_nonexistent_assignment_returns_404():
    driver = register_user(UserRole.DRIVER)

    response = client.post(
        "/api/v1/collection-trackings",
        headers=driver["headers"],
        json={"assignment_id": str(uuid4())},
    )

    assert response.status_code == 404


def test_assignment_must_be_assigned_before_tracking():
    scenario = create_scenario()

    response = client.patch(
        f"/api/v1/collection-assignments/{scenario['assignment']['id']}/status",
        headers=scenario["manager"]["headers"],
        json={"status": "in_progress"},
    )

    assert response.status_code == 200, response.text

    tracking_response = start_tracking(scenario)

    assert tracking_response.status_code == 400


def test_duplicate_tracking_is_rejected():
    scenario = create_scenario()

    first = start_tracking(scenario)
    assert first.status_code == 201, first.text

    second = start_tracking(scenario)

    assert second.status_code == 400
    assert "already exists" in second.json()["detail"].lower()


# ---------------------------------------------------------
# GET AND LIST TRACKING TESTS
# ---------------------------------------------------------

def test_management_can_get_tracking():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    tracking_id = created.json()["id"]

    response = client.get(
        f"/api/v1/collection-trackings/{tracking_id}",
        headers=scenario["manager"]["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == tracking_id


def test_nonexistent_tracking_returns_404():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    response = client.get(
        f"/api/v1/collection-trackings/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404


def test_management_can_list_trackings():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    response = client.get(
        "/api/v1/collection-trackings",
        headers=scenario["manager"]["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_customer_cannot_list_trackings():
    customer = register_user(UserRole.CUSTOMER)

    response = client.get(
        "/api/v1/collection-trackings",
        headers=customer["headers"],
    )

    assert response.status_code == 403


def test_management_can_get_pickup_tracking_history():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    response = client.get(
        (
            "/api/v1/collection-trackings/pickup/"
            f"{scenario['pickup']['id']}/history"
        ),
        headers=scenario["manager"]["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# ---------------------------------------------------------
# UPDATE TRACKING TESTS
# ---------------------------------------------------------

def test_assigned_driver_can_update_tracking():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    tracking_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/collection-trackings/{tracking_id}",
        headers=scenario["driver"]["user"]["headers"],
        json={
            "collected_quantity_kg": 15,
            "remarks": "Collected 15 kg",
            "photo_urls": [
                "https://example.com/collected-waste.jpg"
            ],
        },
    )

    assert response.status_code == 200, response.text
    assert float(response.json()["collected_quantity_kg"]) == 15
    assert response.json()["remarks"] == "Collected 15 kg"


def test_collected_quantity_cannot_exceed_pickup_quantity():
    scenario = create_scenario(quantity=25)
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    response = client.patch(
        f"/api/v1/collection-trackings/{created.json()['id']}",
        headers=scenario["driver"]["user"]["headers"],
        json={"collected_quantity_kg": 30},
    )

    assert response.status_code == 400
    assert "requested quantity" in response.json()["detail"].lower()

def test_collected_quantity_cannot_exceed_vehicle_capacity():
    # First create a valid assignment.
    scenario = create_scenario(quantity=25, capacity=5000)

    # Reduce vehicle capacity after assignment creation.
    with TestingSessionLocal() as db:
        vehicle = db.get(Vehicle, scenario["vehicle"]["id"])
        vehicle.capacity_kg = 12
        db.commit()

    # Start tracking.
    created = client.post(
        "/api/v1/collection-trackings",
        headers=scenario["driver"]["user"]["headers"],
        json={
            "assignment_id": scenario["assignment"]["id"],
        },
    )

    assert created.status_code == 201, created.text

    # Try collecting more than the vehicle capacity.
    response = client.patch(
        f"/api/v1/collection-trackings/{created.json()['id']}",
        headers=scenario["driver"]["user"]["headers"],
        json={
            "collected_quantity_kg": 15,
        },
    )

    assert response.status_code == 400
    assert "vehicle capacity" in response.json()["detail"].lower()

# ---------------------------------------------------------
# TRACKING STATUS TESTS
# ---------------------------------------------------------

def test_driver_can_complete_collection():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    response = client.patch(
        (
            "/api/v1/collection-trackings/"
            f"{created.json()['id']}/status"
        ),
        headers=scenario["driver"]["user"]["headers"],
        json={
            "status": "completed",
            "collected_quantity_kg": 20,
            "remarks": "Collection completed successfully",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None


def test_partial_collection_requires_remarks():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    response = client.patch(
        (
            "/api/v1/collection-trackings/"
            f"{created.json()['id']}/status"
        ),
        headers=scenario["driver"]["user"]["headers"],
        json={
            "status": "partially_completed",
            "collected_quantity_kg": 10,
        },
    )

    assert response.status_code == 422


def test_driver_can_record_partial_collection():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    response = client.patch(
        (
            "/api/v1/collection-trackings/"
            f"{created.json()['id']}/status"
        ),
        headers=scenario["driver"]["user"]["headers"],
        json={
            "status": "partially_completed",
            "collected_quantity_kg": 10,
            "remarks": "Some waste was inaccessible",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "partially_completed"


def test_failed_collection_requires_remarks():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    response = client.patch(
        (
            "/api/v1/collection-trackings/"
            f"{created.json()['id']}/status"
        ),
        headers=scenario["driver"]["user"]["headers"],
        json={"status": "failed"},
    )

    assert response.status_code == 422


def test_driver_can_mark_collection_failed():
    scenario = create_scenario()
    created = start_tracking(scenario)

    assert created.status_code == 201, created.text

    response = client.patch(
        (
            "/api/v1/collection-trackings/"
            f"{created.json()['id']}/status"
        ),
        headers=scenario["driver"]["user"]["headers"],
        json={
            "status": "failed",
            "remarks": "Vehicle could not access the collection area",
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "failed"
