import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

load_dotenv(".env")

os.environ["ENVIRONMENT"] = "development"

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is missing from .env")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from main import app
from db.session import get_db, engine
from models.user import User
from core.constants import UserRole


test_engine = create_engine(TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)

client = TestClient(app)

PASSWORD = "StrongPassword123!"


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module():
    app.dependency_overrides[get_db] = override_get_db

    with test_engine.connect() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE users "
                "RESTART IDENTITY CASCADE"
            )
        )
        connection.commit()


def teardown_module():
    app.dependency_overrides.clear()
    client.close()
    test_engine.dispose()
    engine.dispose()


def unique_email():
    return f"dashboard_{uuid4().hex[:10]}@example.com"


def create_user_and_login(
    role=UserRole.SUPER_ADMIN,
):
    email = unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Dashboard Test User",
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

    assert login_response.status_code == 200, (
        login_response.text
    )

    token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


# --------------------------------------------------
# AUTHENTICATION TESTS
# --------------------------------------------------

def test_admin_dashboard_requires_authentication():
    response = client.get(
        "/api/v1/admin-dashboard/overview"
    )

    assert response.status_code == 401


def test_customer_cannot_access_admin_dashboard():
    headers = create_user_and_login(
        UserRole.CUSTOMER
    )

    response = client.get(
        "/api/v1/admin-dashboard/overview",
        headers=headers,
    )

    assert response.status_code == 403


# --------------------------------------------------
# OVERVIEW TESTS
# --------------------------------------------------

def test_get_admin_dashboard_overview():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/admin-dashboard/overview",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "total_customers" in data
    assert "collections" in data
    assert "vehicles" in data
    assert "recycling" in data
    assert "complaints" in data
    assert "maintenance" in data
    assert "generated_at" in data


def test_get_admin_dashboard_summary():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/admin-dashboard/summary",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    expected_fields = [
        "total_customers",
        "total_collection_requests",
        "completed_collections",
        "pending_pickups",
        "missed_collections",
        "total_vehicles",
        "available_vehicles",
        "active_recycling_centers",
        "total_waste_collected_kg",
        "total_waste_recycled_kg",
        "recycling_efficiency_percentage",
        "pending_complaints",
        "maintenance_status",
    ]

    for field in expected_fields:
        assert field in data


# --------------------------------------------------
# COLLECTION TESTS
# --------------------------------------------------

def test_get_dashboard_collections():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/admin-dashboard/collections",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "total_collection_requests" in data
    assert "completed_collections" in data
    assert "pending_pickups" in data
    assert "missed_collections" in data


# --------------------------------------------------
# VEHICLE TESTS
# --------------------------------------------------

def test_get_dashboard_vehicles():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/admin-dashboard/vehicles",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "total_vehicles" in data
    assert "available_vehicles" in data
    assert "assigned_vehicles" in data
    assert "maintenance_vehicles" in data
    assert "out_of_service_vehicles" in data
    assert "retired_vehicles" in data


# --------------------------------------------------
# RECYCLING TESTS
# --------------------------------------------------

def test_get_dashboard_recycling():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/admin-dashboard/recycling",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "active_recycling_centers" in data
    assert "total_waste_collected_kg" in data
    assert "total_waste_recycled_kg" in data
    assert "recycling_efficiency_percentage" in data


# --------------------------------------------------
# COMPLAINT TESTS
# --------------------------------------------------

def test_get_dashboard_complaints():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/admin-dashboard/complaints",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "total_complaints" in data
    assert "pending_complaints" in data


# --------------------------------------------------
# MAINTENANCE TESTS
# --------------------------------------------------

def test_get_dashboard_maintenance():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/admin-dashboard/maintenance",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "total_maintenance_records" in data
    assert "pending_maintenance" in data
    assert "in_progress_maintenance" in data
    assert "completed_maintenance" in data