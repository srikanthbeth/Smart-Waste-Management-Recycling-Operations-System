
import os
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(".env")

os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:Srik8499@localhost:5433/smart_waste_management_test",
)

from fastapi.testclient import TestClient
from sqlalchemy import text

from core.constants import UserRole
from db.session import SessionLocal, engine
from main import app
from models.user import User


client = TestClient(app)

BASE_URL = "/api/v1/waste-categories"
PASSWORD = "WasteTest@12345"


def unique_email():
    return f"waste_{uuid4().hex[:12]}@example.com"


def cleanup_database():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    waste_categories,
                    locations,
                    password_reset_tokens,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )


def setup_module():
    cleanup_database()


def teardown_module():
    cleanup_database()


def register_user(email=None, password=PASSWORD):
    email = email or unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Waste Test User",
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201, response.text
    return email


def create_user_with_role(role):
    email = register_user()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None

        user.role = role
        db.commit()
    finally:
        db.close()

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


def create_category(headers, name=None, code=None, **overrides):
    payload = {
        "name": name or f"Category {uuid4().hex[:8]}",
        "code": code or f"WASTE_{uuid4().hex[:8].upper()}",
        "description": "Waste category test description",
        "is_recyclable": True,
        "is_hazardous": False,
    }

    payload.update(overrides)

    return client.post(
        BASE_URL,
        json=payload,
        headers=headers,
    )


def test_super_admin_can_create_category():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = create_category(
        headers,
        name="Organic Waste",
        code="ORGANIC",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Organic Waste"
    assert response.json()["code"] == "ORGANIC"
    assert response.json()["is_recyclable"] is True


def test_operations_manager_can_create_category():
    email = create_user_with_role(UserRole.OPERATIONS_MANAGER)
    headers = login_user(email)

    response = create_category(
        headers,
        name="Plastic Waste",
        code="PLASTIC",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Plastic Waste"


def test_customer_cannot_create_category():
    email = create_user_with_role(UserRole.CUSTOMER)
    headers = login_user(email)

    response = create_category(headers)

    assert response.status_code == 403


def test_unauthenticated_user_cannot_create_category():
    response = create_category({})

    assert response.status_code == 401


def test_create_category_normalizes_name_and_code():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = create_category(
        headers,
        name="  Paper Waste  ",
        code="  paper waste  ",
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Paper Waste"
    assert response.json()["code"] == "PAPER_WASTE"


def test_duplicate_category_name_is_rejected():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_response = create_category(
        headers,
        name="Duplicate Waste",
        code="DUPLICATE_1",
    )

    assert create_response.status_code == 201

    duplicate_response = create_category(
        headers,
        name="Duplicate Waste",
        code="DUPLICATE_2",
    )

    assert duplicate_response.status_code == 409


def test_duplicate_category_code_is_rejected():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    first_response = create_category(
        headers,
        name="First Waste",
        code="SAME_CODE",
    )

    assert first_response.status_code == 201

    second_response = create_category(
        headers,
        name="Second Waste",
        code="SAME_CODE",
    )

    assert second_response.status_code == 409


def test_category_name_is_required():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = client.post(
        BASE_URL,
        json={
            "code": "NO_NAME",
            "is_recyclable": True,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_category_code_is_required():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = client.post(
        BASE_URL,
        json={
            "name": "No Code Waste",
            "is_recyclable": True,
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_category_name_cannot_be_too_short():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = create_category(
        headers,
        name="A",
    )

    assert response.status_code == 422


def test_category_code_cannot_be_too_short():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = create_category(
        headers,
        code="A",
    )

    assert response.status_code == 422


def test_category_cannot_have_empty_name():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = create_category(
        headers,
        name="   ",
    )

    assert response.status_code == 422


def test_list_categories():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_category(
        headers,
        name="Glass Waste",
        code="GLASS",
    )

    response = client.get(
        BASE_URL,
        headers=headers,
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)

    names = [item["name"] for item in response.json()]
    assert "Glass Waste" in names


def test_all_authenticated_roles_can_view_categories():
    email = create_user_with_role(UserRole.CUSTOMER)
    headers = login_user(email)

    response = client.get(
        BASE_URL,
        headers=headers,
    )

    assert response.status_code == 200


def test_unauthenticated_user_cannot_list_categories():
    response = client.get(BASE_URL)

    assert response.status_code == 401


def test_get_category_by_id():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_response = create_category(
        headers,
        name="Metal Waste",
        code="METAL",
    )

    category_id = create_response.json()["id"]

    response = client.get(
        f"{BASE_URL}/{category_id}",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == category_id
    assert response.json()["name"] == "Metal Waste"


def test_get_nonexistent_category_returns_404():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = client.get(
        f"{BASE_URL}/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


def test_invalid_category_id_returns_422():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = client.get(
        f"{BASE_URL}/invalid-id",
        headers=headers,
    )

    assert response.status_code == 422


def test_update_category():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_response = create_category(
        headers,
        name="Old Category",
        code="OLD_CATEGORY",
    )

    category_id = create_response.json()["id"]

    response = client.patch(
        f"{BASE_URL}/{category_id}",
        json={
            "name": "Updated Category",
            "description": "Updated description",
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Category"
    assert response.json()["description"] == "Updated description"


def test_operations_manager_can_update_category():
    admin_email = create_user_with_role(UserRole.SUPER_ADMIN)
    admin_headers = login_user(admin_email)

    create_response = create_category(
        admin_headers,
        name="Update Permission Waste",
        code="UPDATE_PERMISSION",
    )

    category_id = create_response.json()["id"]

    manager_email = create_user_with_role(
        UserRole.OPERATIONS_MANAGER
    )
    manager_headers = login_user(manager_email)

    response = client.patch(
        f"{BASE_URL}/{category_id}",
        json={"description": "Updated by manager"},
        headers=manager_headers,
    )

    assert response.status_code == 200


def test_customer_cannot_update_category():
    admin_email = create_user_with_role(UserRole.SUPER_ADMIN)
    admin_headers = login_user(admin_email)

    create_response = create_category(admin_headers)
    category_id = create_response.json()["id"]

    customer_email = create_user_with_role(UserRole.CUSTOMER)
    customer_headers = login_user(customer_email)

    response = client.patch(
        f"{BASE_URL}/{category_id}",
        json={"description": "Unauthorized update"},
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_update_nonexistent_category_returns_404():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = client.patch(
        f"{BASE_URL}/{uuid4()}",
        json={"name": "Updated Name"},
        headers=headers,
    )

    assert response.status_code == 404


def test_update_category_with_duplicate_name_is_rejected():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    first = create_category(
        headers,
        name="Existing Category One",
        code="EXISTING_ONE",
    )
    second = create_category(
        headers,
        name="Existing Category Two",
        code="EXISTING_TWO",
    )

    response = client.patch(
        f"{BASE_URL}/{second.json()['id']}",
        json={"name": "Existing Category One"},
        headers=headers,
    )

    assert response.status_code == 409


def test_update_category_with_duplicate_code_is_rejected():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_category(
        headers,
        name="Code Category One",
        code="CODE_ONE",
    )

    second = create_category(
        headers,
        name="Code Category Two",
        code="CODE_TWO",
    )

    response = client.patch(
        f"{BASE_URL}/{second.json()['id']}",
        json={"code": "CODE_ONE"},
        headers=headers,
    )

    assert response.status_code == 409


def test_update_category_without_fields_is_rejected():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_response = create_category(headers)
    category_id = create_response.json()["id"]

    response = client.patch(
        f"{BASE_URL}/{category_id}",
        json={},
        headers=headers,
    )

    assert response.status_code == 400


def test_update_category_status_to_inactive():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_response = create_category(headers)
    category_id = create_response.json()["id"]

    response = client.patch(
        f"{BASE_URL}/{category_id}/status",
        json={"status": "inactive"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


def test_update_category_status_to_active():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_response = create_category(headers)
    category_id = create_response.json()["id"]

    client.patch(
        f"{BASE_URL}/{category_id}/status",
        json={"status": "inactive"},
        headers=headers,
    )

    response = client.patch(
        f"{BASE_URL}/{category_id}/status",
        json={"status": "active"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_customer_cannot_change_category_status():
    admin_email = create_user_with_role(UserRole.SUPER_ADMIN)
    admin_headers = login_user(admin_email)

    create_response = create_category(admin_headers)
    category_id = create_response.json()["id"]

    customer_email = create_user_with_role(UserRole.CUSTOMER)
    customer_headers = login_user(customer_email)

    response = client.patch(
        f"{BASE_URL}/{category_id}/status",
        json={"status": "inactive"},
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_update_status_for_nonexistent_category_returns_404():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    response = client.patch(
        f"{BASE_URL}/{uuid4()}/status",
        json={"status": "inactive"},
        headers=headers,
    )

    assert response.status_code == 404


def test_invalid_category_status_is_rejected():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_response = create_category(headers)
    category_id = create_response.json()["id"]

    response = client.patch(
        f"{BASE_URL}/{category_id}/status",
        json={"status": "deleted"},
        headers=headers,
    )

    assert response.status_code == 422


def test_filter_categories_by_recyclable_status():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_category(
        headers,
        name="Recyclable Test Waste",
        code="RECYCLABLE_TEST",
        is_recyclable=True,
        is_hazardous=False,
    )

    response = client.get(
        BASE_URL,
        params={"is_recyclable": "true"},
        headers=headers,
    )

    assert response.status_code == 200
    assert all(item["is_recyclable"] is True for item in response.json())


def test_filter_categories_by_hazardous_status():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_category(
        headers,
        name="Hazardous Test Waste",
        code="HAZARDOUS_TEST",
        is_recyclable=False,
        is_hazardous=True,
    )

    response = client.get(
        BASE_URL,
        params={"is_hazardous": "true"},
        headers=headers,
    )

    assert response.status_code == 200
    assert all(item["is_hazardous"] is True for item in response.json())


def test_filter_categories_by_status():
    email = create_user_with_role(UserRole.SUPER_ADMIN)
    headers = login_user(email)

    create_response = create_category(headers)
    category_id = create_response.json()["id"]

    client.patch(
        f"{BASE_URL}/{category_id}/status",
        json={"status": "inactive"},
        headers=headers,
    )

    response = client.get(
        BASE_URL,
        params={"status": "inactive"},
        headers=headers,
    )

    assert response.status_code == 200
    assert all(item["status"] == "inactive" for item in response.json())
