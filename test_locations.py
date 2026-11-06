
import os
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import select, text
from fastapi.testclient import TestClient

load_dotenv()

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:Srik8499@localhost:5433/smart_waste_management_test",
)

from main import app
from db.session import SessionLocal, engine
from models.user import User
from core.constants import UserRole


client = TestClient(app)


def unique_email():
    return f"location_{uuid4().hex[:10]}@example.com"


def cleanup_database():
    with engine.begin() as connection:
        connection.execute(
            text("""
                TRUNCATE TABLE
                    locations,
                    password_reset_tokens,
                    users
                RESTART IDENTITY CASCADE
            """)
        )


def setup_module():
    cleanup_database()


def teardown_module():
    cleanup_database()


def register_user():
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Location Test User",
            "email": email,
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 201, response.text

    return email


def create_user_with_role(role):
    email = register_user()

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.email == email)
        )

        user.role = role
        db.commit()

    return email


def login_user(email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "StrongPass123!",
        },
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"]


def create_token(role=UserRole.SUPER_ADMIN):
    email = create_user_with_role(role)
    return login_user(email)


def auth_headers(token):
    return {
        "Authorization": f"Bearer {token}"
    }


def create_zone(token, code=None):
    return client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Hyderabad Zone",
            "code": code or f"ZONE-{uuid4().hex[:8].upper()}",
            "location_type": "zone",
            "description": "Main collection zone",
            "city": "Hyderabad",
            "state": "Telangana",
        },
    )


# --------------------------------------------------
# CREATE LOCATION TESTS
# --------------------------------------------------


def test_super_admin_can_create_zone():
    token = create_token()

    response = create_zone(token)

    assert response.status_code == 201
    assert response.json()["location_type"] == "zone"
    assert response.json()["status"] == "active"
    assert response.json()["is_active"] is True


def test_operations_manager_can_create_zone():
    token = create_token(UserRole.OPERATIONS_MANAGER)

    response = create_zone(token)

    assert response.status_code == 201


def test_customer_cannot_create_location():
    token = create_token(UserRole.CUSTOMER)

    response = create_zone(token)

    assert response.status_code == 403


def test_unauthenticated_user_cannot_create_location():
    response = create_zone(token="invalid")

    assert response.status_code == 401


def test_duplicate_location_code_rejected():
    token = create_token()
    code = f"ZONE-{uuid4().hex[:8].upper()}"

    first = create_zone(token, code)
    second = create_zone(token, code)

    assert first.status_code == 201
    assert second.status_code == 409


def test_location_name_is_required():
    token = create_token()

    response = client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "",
            "code": f"ZONE-{uuid4().hex[:8].upper()}",
            "location_type": "zone",
        },
    )

    assert response.status_code == 422


def test_invalid_location_type_rejected():
    token = create_token()

    response = client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Invalid Location",
            "code": f"LOC-{uuid4().hex[:8].upper()}",
            "location_type": "invalid_type",
        },
    )

    assert response.status_code == 422


def test_invalid_latitude_rejected():
    token = create_token()

    response = client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Invalid GPS Zone",
            "code": f"ZONE-{uuid4().hex[:8].upper()}",
            "location_type": "zone",
            "latitude": 100,
            "longitude": 78.4,
        },
    )

    assert response.status_code == 422


def test_latitude_and_longitude_must_be_provided_together():
    token = create_token()

    response = client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "GPS Zone",
            "code": f"ZONE-{uuid4().hex[:8].upper()}",
            "location_type": "zone",
            "latitude": 17.4,
        },
    )

    assert response.status_code == 422


# --------------------------------------------------
# LOCATION HIERARCHY TESTS
# --------------------------------------------------


def test_create_ward_under_zone():
    token = create_token()

    zone_response = create_zone(token)
    zone_id = zone_response.json()["id"]

    response = client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Ward 1",
            "code": f"WARD-{uuid4().hex[:8].upper()}",
            "location_type": "ward",
            "parent_id": zone_id,
        },
    )

    assert response.status_code == 201
    assert response.json()["parent_id"] == zone_id
    assert response.json()["location_type"] == "ward"


def test_create_ward_without_parent_rejected():
    token = create_token()

    response = client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Independent Ward",
            "code": f"WARD-{uuid4().hex[:8].upper()}",
            "location_type": "ward",
        },
    )

    assert response.status_code == 400


def test_invalid_parent_type_rejected():
    token = create_token()

    zone_response = create_zone(token)
    zone_id = zone_response.json()["id"]

    response = client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Invalid Area",
            "code": f"AREA-{uuid4().hex[:8].upper()}",
            "location_type": "area",
            "parent_id": zone_id,
        },
    )

    assert response.status_code == 400


def test_nonexistent_parent_rejected():
    token = create_token()

    response = client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Ward 2",
            "code": f"WARD-{uuid4().hex[:8].upper()}",
            "location_type": "ward",
            "parent_id": str(uuid4()),
        },
    )

    assert response.status_code == 404


# --------------------------------------------------
# GET LOCATION TESTS
# --------------------------------------------------


def test_list_locations():
    token = create_token()

    create_zone(token)

    response = client.get(
        "/api/v1/locations",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_location_by_id():
    token = create_token()

    created = create_zone(token)
    location_id = created.json()["id"]

    response = client.get(
        f"/api/v1/locations/{location_id}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == location_id


def test_get_nonexistent_location():
    token = create_token()

    response = client.get(
        f"/api/v1/locations/{uuid4()}",
        headers=auth_headers(token),
    )

    assert response.status_code == 404


def test_customer_can_view_locations():
    admin_token = create_token()

    create_zone(admin_token)

    customer_token = create_token(UserRole.CUSTOMER)

    response = client.get(
        "/api/v1/locations",
        headers=auth_headers(customer_token),
    )

    assert response.status_code == 200


def test_filter_locations_by_type():
    token = create_token()

    create_zone(token)

    response = client.get(
        "/api/v1/locations?location_type=zone",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert all(
        location["location_type"] == "zone"
        for location in response.json()
    )


def test_filter_locations_by_parent():
    token = create_token()

    zone = create_zone(token).json()

    client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Ward 5",
            "code": f"WARD-{uuid4().hex[:8].upper()}",
            "location_type": "ward",
            "parent_id": zone["id"],
        },
    )

    response = client.get(
        f"/api/v1/locations?parent_id={zone['id']}",
        headers=auth_headers(token),
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["parent_id"] == zone["id"]


# --------------------------------------------------
# UPDATE LOCATION TESTS
# --------------------------------------------------


def test_super_admin_can_update_location():
    token = create_token()

    created = create_zone(token)
    location_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/locations/{location_id}",
        headers=auth_headers(token),
        json={
            "name": "Updated Hyderabad Zone",
            "description": "Updated description",
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Hyderabad Zone"


def test_operations_manager_can_update_location():
    admin_token = create_token()

    created = create_zone(admin_token)
    location_id = created.json()["id"]

    manager_token = create_token(UserRole.OPERATIONS_MANAGER)

    response = client.patch(
        f"/api/v1/locations/{location_id}",
        headers=auth_headers(manager_token),
        json={
            "name": "Manager Updated Zone",
        },
    )

    assert response.status_code == 200


def test_customer_cannot_update_location():
    admin_token = create_token()

    created = create_zone(admin_token)
    location_id = created.json()["id"]

    customer_token = create_token(UserRole.CUSTOMER)

    response = client.patch(
        f"/api/v1/locations/{location_id}",
        headers=auth_headers(customer_token),
        json={
            "name": "Unauthorized Update",
        },
    )

    assert response.status_code == 403


def test_update_nonexistent_location():
    token = create_token()

    response = client.patch(
        f"/api/v1/locations/{uuid4()}",
        headers=auth_headers(token),
        json={
            "name": "Missing Location",
        },
    )

    assert response.status_code == 404


# --------------------------------------------------
# LOCATION STATUS TESTS
# --------------------------------------------------


def test_super_admin_can_deactivate_location():
    token = create_token()

    created = create_zone(token)
    location_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/locations/{location_id}/status",
        headers=auth_headers(token),
        json={
            "status": "inactive",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    assert response.json()["is_active"] is False


def test_super_admin_can_activate_location():
    token = create_token()

    created = create_zone(token)
    location_id = created.json()["id"]

    client.patch(
        f"/api/v1/locations/{location_id}/status",
        headers=auth_headers(token),
        json={
            "status": "inactive",
        },
    )

    response = client.patch(
        f"/api/v1/locations/{location_id}/status",
        headers=auth_headers(token),
        json={
            "status": "active",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["is_active"] is True


def test_cannot_deactivate_location_with_children():
    token = create_token()

    zone = create_zone(token).json()

    client.post(
        "/api/v1/locations",
        headers=auth_headers(token),
        json={
            "name": "Ward 10",
            "code": f"WARD-{uuid4().hex[:8].upper()}",
            "location_type": "ward",
            "parent_id": zone["id"],
        },
    )

    response = client.patch(
        f"/api/v1/locations/{zone['id']}/status",
        headers=auth_headers(token),
        json={
            "status": "inactive",
        },
    )

    assert response.status_code == 409


def test_customer_cannot_change_location_status():
    admin_token = create_token()

    created = create_zone(admin_token)
    location_id = created.json()["id"]

    customer_token = create_token(UserRole.CUSTOMER)

    response = client.patch(
        f"/api/v1/locations/{location_id}/status",
        headers=auth_headers(customer_token),
        json={
            "status": "inactive",
        },
    )

    assert response.status_code == 403


def test_invalid_location_status_rejected():
    token = create_token()

    created = create_zone(token)
    location_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/locations/{location_id}/status",
        headers=auth_headers(token),
        json={
            "status": "deleted",
        },
    )

    assert response.status_code == 422
