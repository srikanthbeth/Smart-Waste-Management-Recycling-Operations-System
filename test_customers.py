
import os
from uuid import uuid4

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
from core.constants import UserRole


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


# ---------------------------------------------------------
# CUSTOMER CREATION TESTS
# ---------------------------------------------------------

def test_customer_can_create_profile():
    email, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(headers)

    assert response.status_code == 201

    data = response.json()

    assert data["customer_code"].startswith("CUST-")
    assert data["customer_type"] == "residential"
    assert data["city"] == "Hyderabad"
    assert data["status"] == "active"


def test_customer_profile_has_correct_user_id():
    email, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(headers)

    assert response.status_code == 201

    with SessionLocal() as db:
        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        assert response.json()["user_id"] == str(user.id)


def test_customer_cannot_create_duplicate_profile():
    email, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    first_response = create_customer(headers)

    assert first_response.status_code == 201

    second_response = create_customer(headers)

    assert second_response.status_code == 409


def test_customer_creation_requires_authentication():
    response = client.post(
        "/api/v1/customers",
        json=customer_payload(),
    )

    assert response.status_code == 401


def test_non_customer_cannot_create_profile():
    email, headers = create_user_with_role(
        UserRole.DRIVER
    )

    response = create_customer(headers)

    assert response.status_code == 403


def test_customer_code_is_unique():
    _, headers1 = create_user_with_role(
        UserRole.CUSTOMER
    )

    _, headers2 = create_user_with_role(
        UserRole.CUSTOMER
    )

    response1 = create_customer(headers1)
    response2 = create_customer(headers2)

    assert response1.status_code == 201
    assert response2.status_code == 201

    assert (
        response1.json()["customer_code"]
        != response2.json()["customer_code"]
    )


# ---------------------------------------------------------
# CUSTOMER TYPE VALIDATION TESTS
# ---------------------------------------------------------

def test_commercial_customer_requires_organization_name():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        customer_type="commercial",
    )

    assert response.status_code == 422


def test_commercial_customer_with_organization_name():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        customer_type="commercial",
        organization_name="ABC Shopping Mall",
        property_type="shop",
    )

    assert response.status_code == 201
    assert response.json()["organization_name"] == "ABC Shopping Mall"


def test_industrial_customer_requires_organization_name():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        customer_type="industrial",
    )

    assert response.status_code == 422


def test_institutional_customer_requires_organization_name():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        customer_type="institutional",
    )

    assert response.status_code == 422


def test_residential_customer_cannot_have_organization_name():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        customer_type="residential",
        organization_name="ABC Company",
    )

    assert response.status_code == 422


def test_invalid_customer_type_rejected():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        customer_type="unknown",
    )

    assert response.status_code == 422


def test_invalid_property_type_rejected():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        property_type="unknown",
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# CUSTOMER FIELD VALIDATION TESTS
# ---------------------------------------------------------

def test_customer_requires_service_address():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    payload = customer_payload()
    payload.pop("service_address")

    response = client.post(
        "/api/v1/customers",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422


def test_customer_rejects_short_postal_code():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        postal_code="1",
    )

    assert response.status_code == 422


def test_customer_rejects_invalid_latitude():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        latitude=100,
    )

    assert response.status_code == 422


def test_customer_rejects_invalid_longitude():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        longitude=200,
    )

    assert response.status_code == 422


def test_customer_rejects_zero_monthly_waste_estimate():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        monthly_waste_estimate_kg=0,
    )

    assert response.status_code == 422


def test_customer_rejects_negative_monthly_waste_estimate():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        monthly_waste_estimate_kg=-10,
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# CUSTOMER PROFILE RETRIEVAL TESTS
# ---------------------------------------------------------

def test_customer_can_get_own_profile():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers)

    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/customers/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["city"] == "Hyderabad"


def test_customer_without_profile_gets_404():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = client.get(
        "/api/v1/customers/me",
        headers=headers,
    )

    assert response.status_code == 404


def test_customer_cannot_access_another_customer_profile():
    _, headers1 = create_user_with_role(
        UserRole.CUSTOMER
    )

    _, headers2 = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers1)

    customer_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=headers2,
    )

    assert response.status_code == 403


def test_customer_can_access_own_profile_by_id():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers)

    customer_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/customers/{customer_id}",
        headers=headers,
    )

    assert response.status_code == 200


def test_customer_not_found():
    _, headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    response = client.get(
        f"/api/v1/customers/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# CUSTOMER UPDATE TESTS
# ---------------------------------------------------------

def test_customer_can_update_own_profile():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={
            "city": "Warangal",
            "postal_code": "506001",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["city"] == "Warangal"


def test_customer_cannot_update_another_customer_profile():
    _, headers1 = create_user_with_role(
        UserRole.CUSTOMER
    )

    _, headers2 = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers1)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"city": "Warangal"},
        headers=headers2,
    )

    assert response.status_code == 403


def test_customer_update_rejects_empty_payload():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={},
        headers=headers,
    )

    assert response.status_code == 400


def test_customer_update_rejects_invalid_coordinates():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"latitude": 120},
        headers=headers,
    )

    assert response.status_code == 422


def test_customer_can_update_organization_details():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={
            "customer_type": "commercial",
            "organization_name": "New Business Pvt Ltd",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["customer_type"] == "commercial"
    assert response.json()["organization_name"] == "New Business Pvt Ltd"


def test_customer_cannot_change_to_organization_without_name():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"customer_type": "commercial"},
        headers=headers,
    )

    assert response.status_code == 422


# ---------------------------------------------------------
# CUSTOMER LIST AND FILTER TESTS
# ---------------------------------------------------------

def test_customer_can_list_customers():
    _, admin_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_customer(customer_headers)

    response = client.get(
        "/api/v1/customers",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_customer_cannot_list_all_customers():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = client.get(
        "/api/v1/customers",
        headers=headers,
    )

    assert response.status_code == 403


def test_customer_list_requires_authentication():
    response = client.get("/api/v1/customers")

    assert response.status_code == 401


def test_filter_customers_by_type():
    _, admin_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_customer(
        customer_headers,
        customer_type="commercial",
        organization_name="Test Business",
        property_type="shop",
    )

    response = client.get(
        "/api/v1/customers?customer_type=commercial",
        headers=admin_headers,
    )

    assert response.status_code == 200

    for customer in response.json():
        assert customer["customer_type"] == "commercial"


def test_filter_customers_by_city():
    _, admin_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_customer(
        customer_headers,
        city="Hyderabad",
    )

    response = client.get(
        "/api/v1/customers?city=Hyderabad",
        headers=admin_headers,
    )

    assert response.status_code == 200

    for customer in response.json():
        assert "hyderabad" in customer["city"].lower()


# ---------------------------------------------------------
# CUSTOMER LOCATION VALIDATION TESTS
# ---------------------------------------------------------

def test_customer_cannot_use_nonexistent_location():
    _, headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    response = create_customer(
        headers,
        location_id=str(uuid4()),
    )

    assert response.status_code == 404


# ---------------------------------------------------------
# CUSTOMER STATUS TESTS
# ---------------------------------------------------------

def test_operations_manager_can_suspend_customer():
    _, admin_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(customer_headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}/status",
        json={"status": "suspended"},
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "suspended"


def test_customer_cannot_change_own_status():
    _, admin_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(customer_headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}/status",
        json={"status": "inactive"},
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_customer_cannot_update_suspended_profile():
    _, admin_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(customer_headers)

    customer_id = create_response.json()["id"]

    status_response = client.patch(
        f"/api/v1/customers/{customer_id}/status",
        json={"status": "suspended"},
        headers=admin_headers,
    )

    assert status_response.status_code == 200

    update_response = client.patch(
        f"/api/v1/customers/{customer_id}",
        json={"city": "Warangal"},
        headers=customer_headers,
    )

    assert update_response.status_code == 400


def test_invalid_customer_status_rejected():
    _, admin_headers = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )

    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(customer_headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}/status",
        json={"status": "unknown"},
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_driver_cannot_change_customer_status():
    _, driver_headers = create_user_with_role(
        UserRole.DRIVER
    )

    _, customer_headers = create_user_with_role(
        UserRole.CUSTOMER
    )

    create_response = create_customer(customer_headers)

    customer_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/customers/{customer_id}/status",
        json={"status": "inactive"},
        headers=driver_headers,
    )

    assert response.status_code == 403
