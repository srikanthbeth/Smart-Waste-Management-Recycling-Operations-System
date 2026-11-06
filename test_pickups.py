
import os
from uuid import uuid4
from datetime import date, timedelta

from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv(dotenv_path=".env")

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:Srik8499@localhost:5433/smart_waste_management_test",
)

from fastapi.testclient import TestClient

from db.session import SessionLocal, engine
from main import app
from models.user import User
from models.waste_category import WasteCategory
from models.location import Location
from core.constants import (
    UserRole,
    WasteCategoryStatus,
    LocationType,
    LocationStatus,
)


client = TestClient(app)

PASSWORD = "WasteTest@12345"


# ---------------------------------------------------------
# TEST DATABASE SETUP AND CLEANUP
# ---------------------------------------------------------

def setup_module():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
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


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def unique_email():
    return f"user_{uuid4().hex[:10]}@example.com"


def register_user(role=UserRole.CUSTOMER):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Waste Test User",
            "email": email,
            "password": PASSWORD,
        },
    )

    assert response.status_code in (200, 201), response.text

    with SessionLocal() as db:
        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        assert user is not None

        user.role = role
        db.commit()

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


def category_payload(**overrides):
    payload = {
        "name": f"Organic Waste {uuid4().hex[:6]}",
        "code": f"ORG-{uuid4().hex[:8].upper()}",
        "description": "Organic waste category",
        "is_recyclable": True,
        "is_hazardous": False,
    }

    payload.update(overrides)

    return payload


def create_waste_category(**overrides):
    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    payload = category_payload(**overrides)

    response = client.post(
        "/api/v1/waste-categories",
        json=payload,
        headers=manager_headers
    )

    assert response.status_code == 201, response.text

    return response

def create_inactive_category():
    with SessionLocal() as db:
        category = WasteCategory(
            name=f"Inactive Waste {uuid4().hex[:6]}",
            code=f"INA-{uuid4().hex[:8].upper()}",
            description="Inactive test category",
            is_recyclable=True,
            is_hazardous=False,
            status=WasteCategoryStatus.INACTIVE,
        )

        db.add(category)
        db.commit()
        db.refresh(category)

        return str(category.id)


def create_location():
    with SessionLocal() as db:
        location = Location(
            name=f"Pickup Zone {uuid4().hex[:6]}",
            code=f"PZ-{uuid4().hex[:8].upper()}",
            description="Pickup test zone",
            location_type=LocationType.ZONE,
            status=LocationStatus.ACTIVE,
            is_active=True,
            city="Hyderabad",
            state="Telangana",
        )

        db.add(location)
        db.commit()
        db.refresh(location)

        return str(location.id)


def customer_payload(**overrides):
    payload = {
        "customer_type": "residential",
        "property_type": "house",
        "service_address": "12 Green Street",
        "city": "Hyderabad",
        "state": "Telangana",
        "postal_code": "500001",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "monthly_waste_estimate_kg": 25,
        "notes": "Regular waste collection required",
    }

    payload.update(overrides)

    return payload


def create_customer(headers, **overrides):
    response = client.post(
        "/api/v1/customers",
        json=customer_payload(**overrides),
        headers=headers,
    )

    return response


def create_customer_user():
    email, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(headers)

    assert response.status_code == 201, response.text

    return email, headers


def pickup_payload(category_id, **overrides):
    payload = {
        "waste_category_id": category_id,
        "location_id": None,
        "estimated_quantity_kg": 25,
        "preferred_date": (
            date.today() + timedelta(days=5)
        ).isoformat(),
        "preferred_time_slot": "Morning",
        "pickup_address": "12 Green Street",
        "city": "Hyderabad",
        "postal_code": "500001",
        "special_instructions": "Collect dry waste separately",
    }

    payload.update(overrides)

    return payload


def create_pickup(headers, category_id, **overrides):
    response = client.post(
        "/api/v1/pickups",
        json=pickup_payload(
            category_id,
            **overrides,
        ),
        headers=headers,
    )

    return response


# Create manager headers for category creation.
MANAGER_EMAIL = register_user(UserRole.OPERATIONS_MANAGER)
MANAGER_HEADERS = login_user(MANAGER_EMAIL)


# ---------------------------------------------------------
# PICKUP CREATION TESTS
# ---------------------------------------------------------

def test_customer_can_create_pickup():
    _, headers = create_customer_user()

    category_response = create_waste_category()

    assert category_response.status_code == 201

    category_id = category_response.json()["id"]

    response = create_pickup(headers, category_id)

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["pickup_code"].startswith("PICK-")
    assert data["status"] == "requested"
    assert data["estimated_quantity_kg"] == 25
    assert data["city"] == "Hyderabad"
    assert data["waste_category_id"] == category_id


def test_pickup_creation_requires_authentication():
    category_response = create_waste_category()

    category_id = category_response.json()["id"]

    response = client.post(
        "/api/v1/pickups",
        json=pickup_payload(category_id),
    )

    assert response.status_code == 401


def test_non_customer_cannot_create_pickup():
    _, headers = create_user_with_role(
        UserRole.DRIVER
    )

    category_response = create_waste_category()

    category_id = category_response.json()["id"]

    response = create_pickup(headers, category_id)

    assert response.status_code == 403


def test_customer_must_have_profile_before_pickup():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    category_response = create_waste_category()

    category_id = category_response.json()["id"]

    response = create_pickup(headers, category_id)

    assert response.status_code == 404


def test_customer_can_create_only_one_active_duplicate_pickup():
    _, headers = create_customer_user()

    category_response = create_waste_category()

    category_id = category_response.json()["id"]

    preferred_date = (
        date.today() + timedelta(days=6)
    ).isoformat()

    first_response = create_pickup(
        headers,
        category_id,
        preferred_date=preferred_date,
    )

    assert first_response.status_code == 201

    second_response = create_pickup(
        headers,
        category_id,
        preferred_date=preferred_date,
    )

    assert second_response.status_code == 409


def test_pickup_code_is_unique():
    _, headers1 = create_customer_user()
    _, headers2 = create_customer_user()

    category_response = create_waste_category()

    category_id = category_response.json()["id"]

    response1 = create_pickup(headers1, category_id)
    response2 = create_pickup(headers2, category_id)

    assert response1.status_code == 201
    assert response2.status_code == 201

    assert (
        response1.json()["pickup_code"]
        != response2.json()["pickup_code"]
    )


# ---------------------------------------------------------
# PICKUP CATEGORY VALIDATION TESTS
# ---------------------------------------------------------

def test_pickup_requires_valid_waste_category():
    _, headers = create_customer_user()

    response = create_pickup(
        headers,
        str(uuid4()),
    )

    assert response.status_code == 404


def test_pickup_rejects_inactive_waste_category():
    _, headers = create_customer_user()

    category_id = create_inactive_category()

    response = create_pickup(headers, category_id)

    assert response.status_code == 400


# ---------------------------------------------------------
# PICKUP FIELD VALIDATION TESTS
# ---------------------------------------------------------

def test_pickup_rejects_zero_quantity():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    response = create_pickup(
        headers,
        category_id,
        estimated_quantity_kg=0,
    )

    assert response.status_code == 422


def test_pickup_rejects_negative_quantity():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    response = create_pickup(
        headers,
        category_id,
        estimated_quantity_kg=-10,
    )

    assert response.status_code == 422


def test_pickup_rejects_past_date():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    response = create_pickup(
        headers,
        category_id,
        preferred_date=(
            date.today() - timedelta(days=1)
        ).isoformat(),
    )

    assert response.status_code == 422


def test_pickup_rejects_today_date():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    response = create_pickup(
        headers,
        category_id,
        preferred_date=date.today().isoformat(),
    )

    assert response.status_code == 422


def test_pickup_requires_address():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    payload = pickup_payload(category_id)
    payload.pop("pickup_address")

    response = client.post(
        "/api/v1/pickups",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422


def test_pickup_requires_city():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    payload = pickup_payload(category_id)
    payload.pop("city")

    response = client.post(
        "/api/v1/pickups",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422


def test_pickup_rejects_nonexistent_location():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    response = create_pickup(
        headers,
        category_id,
        location_id=str(uuid4()),
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# PICKUP RETRIEVAL TESTS
# ---------------------------------------------------------

def test_customer_can_list_own_pickups():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers, category_id)

    assert created.status_code == 201

    response = client.get(
        "/api/v1/pickups/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_customer_can_get_own_pickup():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers, category_id)

    pickup_id = created.json()["id"]

    response = client.get(
        f"/api/v1/pickups/{pickup_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == pickup_id


def test_customer_cannot_get_another_customer_pickup():
    _, headers1 = create_customer_user()
    _, headers2 = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers1, category_id)

    pickup_id = created.json()["id"]

    response = client.get(
        f"/api/v1/pickups/{pickup_id}",
        headers=headers2,
    )

    assert response.status_code == 403


def test_customer_get_nonexistent_pickup():
    _, headers = create_customer_user()

    response = client.get(
        f"/api/v1/pickups/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


def test_operations_manager_can_get_pickup():
    _, customer_headers = create_customer_user()
    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(
        customer_headers,
        category_id,
    )

    pickup_id = created.json()["id"]

    response = client.get(
        f"/api/v1/pickups/{pickup_id}",
        headers=manager_headers,
    )

    assert response.status_code == 200


def test_operations_manager_can_list_pickups():
    _, customer_headers = create_customer_user()

    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(
        customer_headers,
        category_id,
    )

    assert created.status_code == 201, created.text

    pickup_id = created.json()["id"]

    response = client.get(
        "/api/v1/pickups",
        headers=manager_headers,
    )

    assert response.status_code == 200

    pickup_ids = [
        pickup["id"]
        for pickup in response.json()
    ]

    assert pickup_id in pickup_ids

def test_customer_cannot_list_all_pickups():
    _, headers = create_customer_user()

    response = client.get(
        "/api/v1/pickups",
        headers=headers,
    )

    assert response.status_code == 403


def test_pickup_list_requires_authentication():
    response = client.get("/api/v1/pickups")

    assert response.status_code == 401


# ---------------------------------------------------------
# PICKUP UPDATE TESTS
# ---------------------------------------------------------

def test_customer_can_update_own_requested_pickup():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers, category_id)

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}",
        json={
            "pickup_address": "Updated Green Street",
            "special_instructions": "Updated instructions",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["pickup_address"] == "Updated Green Street"


def test_customer_cannot_update_another_customer_pickup():
    _, headers1 = create_customer_user()
    _, headers2 = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers1, category_id)

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}",
        json={"pickup_address": "Another Address"},
        headers=headers2,
    )

    assert response.status_code == 403


def test_customer_cannot_update_pickup_with_empty_payload():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers, category_id)

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}",
        json={},
        headers=headers,
    )

    assert response.status_code == 400


# ---------------------------------------------------------
# PICKUP STATUS TESTS
# ---------------------------------------------------------

def test_operations_manager_can_approve_pickup():
    _, customer_headers = create_customer_user()
    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(
        customer_headers,
        category_id,
    )

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={"status": "approved"},
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_operations_manager_can_reject_pickup():
    _, customer_headers = create_customer_user()
    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(
        customer_headers,
        category_id,
    )

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={
            "status": "rejected",
            "rejection_reason": "Service unavailable",
        },
        headers=manager_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

def test_reject_pickup_requires_reason():
    _, customer_headers = create_customer_user()

    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(
        customer_headers,
        category_id,
    )

    assert created.status_code == 201, created.text

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={
            "status": "rejected"
        },
        headers=manager_headers,
    )

    assert response.status_code == 422

def test_customer_can_cancel_own_pickup():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers, category_id)

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={
            "status": "cancelled",
            "cancellation_reason": "No longer required",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_customer_cannot_cancel_another_customer_pickup():
    _, headers1 = create_customer_user()
    _, headers2 = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers1, category_id)

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={
            "status": "cancelled",
            "cancellation_reason": "Not my pickup",
        },
        headers=headers2,
    )

    assert response.status_code == 403


def test_customer_cannot_approve_pickup():
    _, headers = create_customer_user()

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(headers, category_id)

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={"status": "approved"},
        headers=headers,
    )

    assert response.status_code == 403


def test_invalid_pickup_status_transition_rejected():
    _, customer_headers = create_customer_user()
    _, manager_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(
        customer_headers,
        category_id,
    )

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={"status": "completed"},
        headers=manager_headers,
    )

    assert response.status_code == 400


def test_driver_cannot_approve_pickup():
    _, customer_headers = create_customer_user()
    _, driver_headers = create_user_with_role(
        UserRole.DRIVER
    )

    category_response = create_waste_category()
    category_id = category_response.json()["id"]

    created = create_pickup(
        customer_headers,
        category_id,
    )

    pickup_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/pickups/{pickup_id}/status",
        json={"status": "approved"},
        headers=driver_headers,
    )

    assert response.status_code == 403
