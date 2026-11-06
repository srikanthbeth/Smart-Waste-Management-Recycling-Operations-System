
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# --------------------------------------------------
# TEST DATABASE CONFIGURATION
# --------------------------------------------------

load_dotenv(".env")

os.environ["ENVIRONMENT"] = "development"

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is missing from .env")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

# Import application modules after setting DATABASE_URL
from main import app
from db.session import get_db, engine
from models.user import User
from core.constants import UserRole


test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    expire_on_commit=False,
)

client = TestClient(app)

PASSWORD = "StrongPassword123!"


# --------------------------------------------------
# DATABASE SETUP AND CLEANUP
# --------------------------------------------------

def override_get_db():
    db = TestingSessionLocal()

    try:
        yield db
    finally:
        db.close()


def setup_module():
    app.dependency_overrides[get_db] = override_get_db

    tables = """
        collection_performance_snapshots,
        complaint_histories,
        customer_complaints,
        vehicle_maintenances,
        waste_disposals,
        waste_processings,
        waste_segregations,
        waste_transfers,
        recycling_center_waste_categories,
        recycling_centers,
        collection_trackings,
        collection_assignment_field_workers,
        collection_assignments,
        field_workers,
        drivers,
        vehicles,
        pickups,
        customers,
        waste_categories,
        locations,
        password_reset_tokens,
        users
    """

    with test_engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
        )


def teardown_module():
    app.dependency_overrides.clear()
    client.close()
    test_engine.dispose()
    engine.dispose()


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def unique_email():
    return f"performance_{uuid4().hex[:10]}@example.com"


def create_user_and_login(role=UserRole.SUPER_ADMIN):
    email = unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Performance Test User",
            "email": email,
            "password": PASSWORD,
        },
    )

    assert register_response.status_code in (200, 201), (
        register_response.text
    )

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

    finally:
        db.close()

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": PASSWORD,
        },
    )

    assert login_response.status_code == 200, login_response.text

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

def test_collection_performance_requires_authentication():
    response = client.get(
        "/api/v1/collection-performance/summary"
    )

    assert response.status_code == 401


# --------------------------------------------------
# SUMMARY ANALYTICS
# --------------------------------------------------

def test_get_collection_performance_summary():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/collection-performance/summary",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "total_pickup_requests" in data
    assert "completed_pickups" in data
    assert "missed_pickups" in data
    assert "average_collection_time_minutes" in data
    assert "collection_efficiency_percentage" in data
    assert "active_vehicles" in data
    assert "utilized_vehicles" in data
    assert "vehicle_utilization_percentage" in data

    assert data["total_pickup_requests"] == 0
    assert data["completed_pickups"] == 0
    assert data["missed_pickups"] == 0


def test_get_collection_performance_summary_with_date_filter():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/collection-performance/summary",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total_pickup_requests"] == 0
    assert data["completed_pickups"] == 0


# --------------------------------------------------
# ZONE-WISE PERFORMANCE
# --------------------------------------------------

def test_get_zone_collection_performance():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/collection-performance/zones",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert isinstance(data, list)


def test_get_zone_collection_performance_with_date_filter():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/collection-performance/zones",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    assert isinstance(response.json(), list)


# --------------------------------------------------
# DRIVER-WISE PERFORMANCE
# --------------------------------------------------

def test_get_driver_collection_performance():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/collection-performance/drivers",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert isinstance(data, list)


def test_get_driver_collection_performance_with_date_filter():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/collection-performance/drivers",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    assert isinstance(response.json(), list)


# --------------------------------------------------
# VEHICLE-WISE PERFORMANCE
# --------------------------------------------------

def test_get_vehicle_collection_performance():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/collection-performance/vehicles",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert isinstance(data, list)


def test_get_vehicle_collection_performance_with_date_filter():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/collection-performance/vehicles",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    assert isinstance(response.json(), list)


# --------------------------------------------------
# ROLE-BASED ACCESS
# --------------------------------------------------

def test_customer_cannot_access_collection_performance():
    headers = create_user_and_login(UserRole.CUSTOMER)

    response = client.get(
        "/api/v1/collection-performance/summary",
        headers=headers,
    )

    assert response.status_code == 403
