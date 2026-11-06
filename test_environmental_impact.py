
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
        environmental_impact_snapshots,
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
    return f"environmental_{uuid4().hex[:10]}@example.com"


def create_user_and_login(role=UserRole.SUPER_ADMIN):
    email = unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Environmental Test User",
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

def test_environmental_impact_requires_authentication():
    response = client.get(
        "/api/v1/environmental-impact/summary"
    )

    assert response.status_code == 401


# --------------------------------------------------
# ENVIRONMENTAL IMPACT SUMMARY
# --------------------------------------------------

def test_get_environmental_impact_summary():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/environmental-impact/summary",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "total_waste_collected_kg" in data
    assert "total_recyclable_waste_kg" in data
    assert "total_waste_recycled_kg" in data
    assert "total_waste_disposed_kg" in data
    assert "recycling_rate_percentage" in data

    assert float(data["total_waste_collected_kg"]) == 0
    assert float(data["total_recyclable_waste_kg"]) == 0
    assert float(data["total_waste_recycled_kg"]) == 0
    assert float(data["total_waste_disposed_kg"]) == 0
    assert float(data["recycling_rate_percentage"]) == 0


def test_get_environmental_impact_summary_with_date_filter():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/environmental-impact/summary",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["total_waste_collected_kg"] == 0
    assert data["total_waste_recycled_kg"] == 0


def test_environmental_impact_summary_invalid_date_range():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/environmental-impact/summary",
        params={
            "start_date": "2026-12-31",
            "end_date": "2026-01-01",
        },
        headers=headers,
    )

    assert response.status_code in (400, 422), response.text


# --------------------------------------------------
# WASTE CATEGORY DISTRIBUTION
# --------------------------------------------------

def test_get_waste_category_distribution():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/environmental-impact/categories",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert isinstance(data, list)


def test_get_waste_category_distribution_requires_authentication():
    response = client.get(
        "/api/v1/environmental-impact/categories"
    )

    assert response.status_code == 401


# --------------------------------------------------
# MONTHLY RECYCLING TRENDS
# --------------------------------------------------

def test_get_monthly_recycling_trends():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/environmental-impact/monthly-trends",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert isinstance(data, list)


def test_get_monthly_recycling_trends_with_date_filter():
    headers = create_user_and_login()

    response = client.get(
        "/api/v1/environmental-impact/monthly-trends",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    assert isinstance(response.json(), list)


# --------------------------------------------------
# ENVIRONMENTAL IMPACT SNAPSHOTS
# --------------------------------------------------

def test_create_environmental_impact_snapshot():
    headers = create_user_and_login()

    response = client.post(
        "/api/v1/environmental-impact/snapshots",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
        headers=headers,
    )

    assert response.status_code in (200, 201), response.text

    data = response.json()

    assert "id" in data
    assert "total_waste_collected_kg" in data
    assert "total_recyclable_waste_kg" in data
    assert "total_waste_recycled_kg" in data
    assert "total_waste_disposed_kg" in data
    assert "recycling_rate_percentage" in data
    assert "waste_category_distribution" in data
    assert "monthly_recycling_trends" in data
    assert "environmental_summary" in data


def test_get_environmental_impact_snapshots():
    headers = create_user_and_login()

    create_response = client.post(
        "/api/v1/environmental-impact/snapshots",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
        },
        headers=headers,
    )

    assert create_response.status_code in (200, 201), (
        create_response.text
    )

    created_snapshot_id = create_response.json()["id"]

    response = client.get(
        "/api/v1/environmental-impact/snapshots",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    snapshot_ids = [item["id"] for item in data]

    assert created_snapshot_id in snapshot_ids
    

def test_get_environmental_impact_snapshot_by_id():
    headers = create_user_and_login()

    create_response = client.post(
        "/api/v1/environmental-impact/snapshots",
        headers=headers,
    )

    assert create_response.status_code in (200, 201), (
        create_response.text
    )

    snapshot_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/environmental-impact/snapshots/{snapshot_id}",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["id"] == snapshot_id


def test_get_nonexistent_environmental_impact_snapshot():
    headers = create_user_and_login()

    snapshot_id = str(uuid4())

    response = client.get(
        f"/api/v1/environmental-impact/snapshots/{snapshot_id}",
        headers=headers,
    )

    assert response.status_code == 404


# --------------------------------------------------
# ROLE-BASED ACCESS
# --------------------------------------------------

def test_customer_cannot_access_environmental_impact():
    headers = create_user_and_login(UserRole.CUSTOMER)

    response = client.get(
        "/api/v1/environmental-impact/summary",
        headers=headers,
    )

    assert response.status_code == 403


def test_customer_cannot_create_environmental_impact_snapshot():
    headers = create_user_and_login(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/environmental-impact/snapshots",
        headers=headers,
    )

    assert response.status_code == 403
