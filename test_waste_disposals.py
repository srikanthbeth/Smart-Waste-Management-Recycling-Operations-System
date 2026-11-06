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
from models.waste_processing import WasteProcessing

from core.constants import (
    UserRole,
    PickupStatus,
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
    return f"disposal_{uuid4().hex[:10]}@example.com"


def register_user(role):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"Disposal {role.value}",
            "email": email,
            "password": "StrongPass123!",
            "phone_number": "9876543210",
        },
    )

    assert response.status_code in (200, 201), response.text

    with TestingSessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()

        assert user is not None

        user.role = role
        user.is_active = True
        user.is_verified = True

        db.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "StrongPass123!",
        },
    )

    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]

    with TestingSessionLocal() as db:
        user = db.query(User).filter(User.email == email).first()
        user_id = str(user.id)

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
            "name": f"Disposal Zone {uuid4().hex[:6]}",
            "code": f"DZ-{uuid4().hex[:8].upper()}",
            "location_type": "zone",
            "description": "Disposal test zone",
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
            "name": f"Disposal Waste {uuid4().hex[:6]}",
            "code": f"DW-{uuid4().hex[:8].upper()}",
            "description": "Disposal test category",
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
            "notes": "Disposal test customer",
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
            "special_instructions": "Disposal test pickup",
        },
    )

    assert response.status_code == 201, response.text

    pickup = response.json()

    with TestingSessionLocal() as db:
        db_pickup = db.get(Pickup, pickup["id"])
        db_pickup.status = PickupStatus.COMPLETED
        db.commit()

    return pickup


def create_vehicle(manager):
    unique = uuid4().hex[:8].upper()

    response = client.post(
        "/api/v1/vehicles",
        headers=manager["headers"],
        json={
            "vehicle_code": f"DISP-VEH-{unique}",
            "registration_number": f"TS09{unique[:6]}",
            "vehicle_type": "truck",
            "make": "Tata",
            "model": "407",
            "manufacturing_year": date.today().year - 2,
            "fuel_type": "diesel",
            "capacity_kg": 5000,
            "current_odometer_km": 25000,
            "location_id": None,
            "notes": "Disposal test vehicle",
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_center(manager, location, category):
    response = client.post(
        "/api/v1/recycling-centers",
        headers=manager["headers"],
        json={
            "name": f"Disposal Center {uuid4().hex[:8]}",
            "code": f"DC-{uuid4().hex[:8].upper()}",
            "description": "Disposal test center",
            "location_id": location["id"],
            "manager_user_id": manager["user_id"],
            "processing_capacity_kg_per_day": 1000,
            "is_available": True,
            "accepted_waste_category_ids": [category["id"]],
        },
    )

    assert response.status_code == 201, response.text
    return response.json()


def create_processing(manager):
    location = create_location(manager)
    category = create_category(manager)
    customer = create_customer(manager)

    pickup = create_pickup(
        manager,
        customer,
        category,
        location,
    )

    vehicle = create_vehicle(manager)

    center = create_center(
        manager,
        location,
        category,
    )

    transfer_response = client.post(
        "/api/v1/waste-transfers",
        headers=manager["headers"],
        json={
            "pickup_id": pickup["id"],
            "source_location_id": location["id"],
            "recycling_center_id": center["id"],
            "waste_category_id": category["id"],
            "vehicle_id": vehicle["id"],
            "quantity_kg": 40,
            "remarks": "Disposal test transfer",
        },
    )

    assert transfer_response.status_code == 201, transfer_response.text
    transfer = transfer_response.json()

    dispatch = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/dispatch",
        headers=manager["headers"],
        json={},
    )
    assert dispatch.status_code == 200, dispatch.text

    transit = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/in-transit",
        headers=manager["headers"],
    )
    assert transit.status_code == 200, transit.text

    receive = client.post(
        f"/api/v1/waste-transfers/{transfer['id']}/receive",
        headers=manager["headers"],
        json={"received_quantity_kg": 40},
    )
    assert receive.status_code == 200, receive.text

    transfer = receive.json()

    segregation_response = client.post(
        "/api/v1/waste-segregations",
        headers=manager["headers"],
        json={
            "transfer_id": transfer["id"],
            "incoming_quantity_kg": 40,
            "recyclable_quantity_kg": 25,
            "non_recyclable_quantity_kg": 10,
            "contaminated_quantity_kg": 5,
            "remarks": "Disposal test segregation",
        },
    )

    assert segregation_response.status_code == 201, segregation_response.text
    segregation = segregation_response.json()

    processing_response = client.post(
        "/api/v1/waste-processings",
        headers=manager["headers"],
        json={
            "segregation_id": segregation["id"],
            "processing_method": "composting",
            "processing_quantity_kg": 10,
            "output_quantity_kg": 7,
            "residual_quantity_kg": 2,
            "processing_loss_kg": 1,
            "remarks": "Disposal test processing",
        },
    )

    assert processing_response.status_code == 201, processing_response.text

    return processing_response.json()


def create_disposal_payload(manager):
    processing = create_processing(manager)

    return processing, {
        "processing_id": processing["id"],
        "disposal_method": "landfill",
        "disposal_site": "Hyderabad Waste Disposal Site",
        "disposal_quantity_kg": 1,
        "remarks": "Disposal test record",
    }


def create_disposal(manager):
    processing, payload = create_disposal_payload(manager)

    response = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text

    return response.json(), processing


# ---------------------------------------------------------
# DATABASE SETUP
# ---------------------------------------------------------

def setup_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    waste_disposals,
                    waste_processings,
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
                    waste_disposals,
                    waste_processings,
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

def test_operations_manager_can_create_disposal():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    processing, payload = create_disposal_payload(manager)

    response = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text

    result = response.json()

    assert result["processing_id"] == processing["id"]
    assert result["disposal_method"] == "landfill"
    assert result["disposal_site"] == payload["disposal_site"]
    assert float(result["disposal_quantity_kg"]) == 1
    assert result["status"] == "partially_disposed"
    assert result["disposed_by_user_id"] == manager["user_id"]
    assert result["disposal_number"].startswith("WD-")


def test_super_admin_can_create_disposal():
    admin = register_user(UserRole.SUPER_ADMIN)
    _, payload = create_disposal_payload(admin)

    response = client.post(
        "/api/v1/waste-disposals",
        headers=admin["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text


def test_disposal_requires_authentication():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_disposal_payload(manager)

    response = client.post(
        "/api/v1/waste-disposals",
        json=payload,
    )

    assert response.status_code == 401


def test_customer_cannot_create_disposal():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)
    _, payload = create_disposal_payload(manager)

    response = client.post(
        "/api/v1/waste-disposals",
        headers=customer["headers"],
        json=payload,
    )

    assert response.status_code == 403


def test_nonexistent_processing_returns_404():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_disposal_payload(manager)

    payload["processing_id"] = str(uuid4())

    response = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 404


def test_disposal_quantity_must_be_positive():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_disposal_payload(manager)

    payload["disposal_quantity_kg"] = 0

    response = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 422


def test_negative_disposal_quantity_is_rejected():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_disposal_payload(manager)

    payload["disposal_quantity_kg"] = -1

    response = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 422


def test_disposal_cannot_exceed_residual_quantity():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_disposal_payload(manager)

    payload["disposal_quantity_kg"] = 3

    response = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 400
    assert "available" in response.json()["detail"].lower()


def test_previously_disposed_quantity_is_deducted():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    processing, payload = create_disposal_payload(manager)

    first = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert first.status_code == 201, first.text

    second_payload = payload.copy()
    second_payload["disposal_quantity_kg"] = 1.5

    second = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=second_payload,
    )

    assert second.status_code == 400
    assert "available" in second.json()["detail"].lower()


def test_disposal_status_becomes_completed_when_residual_is_fully_disposed():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    _, payload = create_disposal_payload(manager)

    payload["disposal_quantity_kg"] = 2

    response = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "completed"


def test_management_can_get_disposal():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    disposal, _ = create_disposal(manager)

    response = client.get(
        f"/api/v1/waste-disposals/{disposal['id']}",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert response.json()["id"] == disposal["id"]


def test_nonexistent_disposal_returns_404():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    response = client.get(
        f"/api/v1/waste-disposals/{uuid4()}",
        headers=manager["headers"],
    )

    assert response.status_code == 404


def test_management_can_list_disposals():
    manager = register_user(UserRole.OPERATIONS_MANAGER)

    create_disposal(manager)
    create_disposal(manager)

    response = client.get(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) >= 2


def test_customer_cannot_list_disposals():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)

    create_disposal(manager)

    response = client.get(
        "/api/v1/waste-disposals",
        headers=customer["headers"],
    )

    assert response.status_code == 403


def test_management_can_view_processing_disposal_history():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    disposal, processing = create_disposal(manager)

    response = client.get(
        f"/api/v1/waste-disposals/processing/{processing['id']}/history",
        headers=manager["headers"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == disposal["id"]


def test_customer_cannot_view_disposal_history():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    customer = register_user(UserRole.CUSTOMER)

    _, processing = create_disposal(manager)

    response = client.get(
        f"/api/v1/waste-disposals/processing/{processing['id']}/history",
        headers=customer["headers"],
    )

    assert response.status_code == 403


def test_processing_without_residual_waste_cannot_be_disposed():
    manager = register_user(UserRole.OPERATIONS_MANAGER)
    processing, payload = create_disposal_payload(manager)

    with TestingSessionLocal() as db:
        db_processing = db.get(WasteProcessing, processing["id"])
        db_processing.residual_quantity_kg = 0
        db.commit()

    response = client.post(
        "/api/v1/waste-disposals",
        headers=manager["headers"],
        json=payload,
    )

    assert response.status_code == 400
    assert "residual waste" in response.json()["detail"].lower()