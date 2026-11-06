import os
from datetime import date
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


def unique_email():
    return f"maintenance_{uuid4().hex[:10]}@example.com"


def register_user(role=UserRole.SUPER_ADMIN):
    email = unique_email()
    password = "StrongPass123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"Maintenance {role.value}",
            "email": email,
            "password": password,
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

    finally:
        db.close()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def create_vehicle(headers):
    unique = uuid4().hex[:8].upper()

    payload = {
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
        "notes": "Vehicle maintenance test vehicle",
    }

    response = client.post(
        "/api/v1/vehicles",
        json=payload,
        headers=headers,
    )

    assert response.status_code in (200, 201), response.text

    return response.json()["id"]


def create_maintenance(headers, vehicle_id, maintenance_type="corrective"):
    payload = {
        "vehicle_id": vehicle_id,
        "maintenance_type": maintenance_type,
        "priority": "medium",
        "title": "Engine maintenance",
        "description": "Engine inspection and maintenance",
        "maintenance_cost": 2500,
        "service_provider": "ABC Vehicle Services",
    }

    if maintenance_type == "preventive":
        payload["scheduled_date"] = str(date.today())

    if maintenance_type == "breakdown":
        payload["breakdown_report"] = "Vehicle engine stopped working"

    response = client.post(
        "/api/v1/vehicle-maintenances",
        json=payload,
        headers=headers,
    )

    return response


def setup_module():
    with engine.connect() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE vehicle_maintenances "
                "RESTART IDENTITY CASCADE"
            )
        )
        connection.commit()


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()


def test_create_maintenance():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(headers, vehicle_id)

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["vehicle_id"] == vehicle_id
    assert data["maintenance_type"] == "corrective"
    assert data["status"] == "requested"
    assert data["maintenance_number"].startswith("VM-")


def test_create_preventive_maintenance():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(
        headers,
        vehicle_id,
        "preventive",
    )

    assert response.status_code == 201, response.text
    assert response.json()["status"] == "scheduled"


def test_preventive_maintenance_requires_schedule():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = client.post(
        "/api/v1/vehicle-maintenances",
        json={
            "vehicle_id": vehicle_id,
            "maintenance_type": "preventive",
            "title": "Preventive service",
            "description": "Regular preventive maintenance",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "Scheduled date" in response.json()["detail"]


def test_breakdown_requires_report():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = client.post(
        "/api/v1/vehicle-maintenances",
        json={
            "vehicle_id": vehicle_id,
            "maintenance_type": "breakdown",
            "title": "Vehicle breakdown",
            "description": "Vehicle stopped working",
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "Breakdown report" in response.json()["detail"]


def test_create_breakdown_report():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(
        headers,
        vehicle_id,
        "breakdown",
    )

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["maintenance_type"] == "breakdown"
    assert data["breakdown_report"] == "Vehicle engine stopped working"
    assert data["downtime_start"] is not None


def test_maintenance_requires_authentication():
    response = client.get("/api/v1/vehicle-maintenances")

    assert response.status_code == 401


def test_customer_cannot_create_maintenance():
    headers = register_user(UserRole.CUSTOMER)
    vehicle_id = create_vehicle(register_user())

    response = create_maintenance(headers, vehicle_id)

    assert response.status_code == 403


def test_invalid_vehicle_returns_404():
    headers = register_user()

    response = client.post(
        "/api/v1/vehicle-maintenances",
        json={
            "vehicle_id": str(uuid4()),
            "maintenance_type": "corrective",
            "title": "Engine maintenance",
            "description": "Engine inspection",
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_negative_maintenance_cost_rejected():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = client.post(
        "/api/v1/vehicle-maintenances",
        json={
            "vehicle_id": vehicle_id,
            "maintenance_type": "corrective",
            "title": "Engine maintenance",
            "description": "Engine inspection",
            "maintenance_cost": -100,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_assign_technician_and_update_status():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(headers, vehicle_id)

    assert response.status_code == 201, response.text

    maintenance_id = response.json()["id"]

    db = TestingSessionLocal()

    try:
        technician = (
            db.query(User)
            .filter(User.email == next(iter(
                [
                    user.email
                    for user in db.query(User).all()
                    if user.role == UserRole.SUPER_ADMIN
                ]
            )))
            .first()
        )

        technician_id = str(technician.id)

    finally:
        db.close()

    update_response = client.patch(
        f"/api/v1/vehicle-maintenances/{maintenance_id}",
        json={
            "technician_id": technician_id,
            "status": "in_progress",
        },
        headers=headers,
    )

    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["technician_id"] == technician_id
    assert update_response.json()["status"] == "in_progress"


def test_complete_maintenance():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(
        headers,
        vehicle_id,
        "breakdown",
    )

    assert response.status_code == 201, response.text

    maintenance_id = response.json()["id"]

    update_response = client.patch(
        f"/api/v1/vehicle-maintenances/{maintenance_id}",
        json={
            "status": "completed",
            "maintenance_cost": 3500,
            "resolution_remarks": "Engine repaired successfully",
        },
        headers=headers,
    )

    assert update_response.status_code == 200, update_response.text

    data = update_response.json()

    assert data["status"] == "completed"
    assert data["completed_at"] is not None
    assert data["downtime_end"] is not None
    assert data["downtime_hours"] is not None


def test_get_maintenance_by_id():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(headers, vehicle_id)

    maintenance_id = response.json()["id"]

    get_response = client.get(
        f"/api/v1/vehicle-maintenances/{maintenance_id}",
        headers=headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == maintenance_id


def test_list_maintenance():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(headers, vehicle_id)

    assert response.status_code == 201

    list_response = client.get(
        "/api/v1/vehicle-maintenances",
        headers=headers,
    )

    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)
    assert len(list_response.json()) >= 1


def test_vehicle_maintenance_history():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(headers, vehicle_id)

    assert response.status_code == 201

    history_response = client.get(
        f"/api/v1/vehicle-maintenances/vehicle/{vehicle_id}/history",
        headers=headers,
    )

    assert history_response.status_code == 200
    assert len(history_response.json()) >= 1


def test_update_maintenance_cost():
    headers = register_user()
    vehicle_id = create_vehicle(headers)

    response = create_maintenance(headers, vehicle_id)

    maintenance_id = response.json()["id"]

    update_response = client.patch(
        f"/api/v1/vehicle-maintenances/{maintenance_id}",
        json={
            "maintenance_cost": 5000,
        },
        headers=headers,
    )

    assert update_response.status_code == 200
    assert float(update_response.json()["maintenance_cost"]) == 5000