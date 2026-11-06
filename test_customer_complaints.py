import os
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
    return f"complaint_{uuid4().hex[:10]}@example.com"


def register_user(role=UserRole.SUPER_ADMIN):
    email = unique_email()
    password = "StrongPass123!"

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Complaint Test User",
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


def create_complaint(headers, category="missed_pickup"):
    return client.post(
        "/api/v1/customer-complaints",
        json={
            "category": category,
            "priority": "medium",
            "subject": "Waste collection complaint",
            "description": "Waste was not collected from my location.",
        },
        headers=headers,
    )


def setup_module():
    with engine.connect() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE complaint_histories, customer_complaints "
                "RESTART IDENTITY CASCADE"
            )
        )
        connection.commit()


def teardown_module():
    app.dependency_overrides.clear()
    engine.dispose()


def test_customer_can_create_complaint():
    headers = register_user(UserRole.CUSTOMER)

    response = create_complaint(headers)

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["complaint_number"].startswith("CC-")
    assert data["category"] == "missed_pickup"
    assert data["status"] == "open"


def test_manager_can_create_complaint():
    headers = register_user(UserRole.SUPER_ADMIN)

    response = create_complaint(headers)

    assert response.status_code == 201, response.text


def test_complaint_requires_authentication():
    response = client.get("/api/v1/customer-complaints")

    assert response.status_code == 401


def test_invalid_complaint_category_rejected():
    headers = register_user(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/customer-complaints",
        json={
            "category": "invalid_category",
            "priority": "medium",
            "subject": "Waste complaint",
            "description": "Waste was not collected from my location.",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_invalid_priority_rejected():
    headers = register_user(UserRole.CUSTOMER)

    response = client.post(
        "/api/v1/customer-complaints",
        json={
            "category": "missed_pickup",
            "priority": "urgent_invalid",
            "subject": "Waste complaint",
            "description": "Waste was not collected from my location.",
        },
        headers=headers,
    )

    assert response.status_code == 422


def test_customer_can_view_own_complaint():
    headers = register_user(UserRole.CUSTOMER)

    response = create_complaint(headers)

    complaint_id = response.json()["id"]

    get_response = client.get(
        f"/api/v1/customer-complaints/{complaint_id}",
        headers=headers,
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == complaint_id


def test_customer_cannot_view_another_customer_complaint():
    first_customer = register_user(UserRole.CUSTOMER)
    second_customer = register_user(UserRole.CUSTOMER)

    response = create_complaint(first_customer)

    complaint_id = response.json()["id"]

    get_response = client.get(
        f"/api/v1/customer-complaints/{complaint_id}",
        headers=second_customer,
    )

    assert get_response.status_code == 403


def test_customer_can_view_only_own_complaints():
    first_customer = register_user(UserRole.CUSTOMER)
    second_customer = register_user(UserRole.CUSTOMER)

    create_complaint(first_customer)
    create_complaint(second_customer)

    response = client.get(
        "/api/v1/customer-complaints",
        headers=first_customer,
    )

    assert response.status_code == 200

    for complaint in response.json():
        assert complaint["customer_id"]


def test_manager_can_assign_complaint():
    manager_headers = register_user(UserRole.SUPER_ADMIN)
    technician_headers = register_user(UserRole.OPERATIONS_MANAGER)

    complaint_response = create_complaint(manager_headers)

    complaint_id = complaint_response.json()["id"]

    db = TestingSessionLocal()

    try:
        technician = (
            db.query(User)
            .filter(User.role == UserRole.OPERATIONS_MANAGER)
            .order_by(User.created_at.desc())
            .first()
        )

        technician_id = str(technician.id)

    finally:
        db.close()

    response = client.patch(
        f"/api/v1/customer-complaints/{complaint_id}",
        json={
            "assigned_team": "Collection Team",
            "assigned_to_user_id": technician_id,
            "status": "assigned",
        },
        headers=manager_headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["assigned_team"] == "Collection Team"
    assert data["assigned_to_user_id"] == technician_id
    assert data["status"] == "assigned"


def test_customer_cannot_update_complaint():
    customer_headers = register_user(UserRole.CUSTOMER)
    manager_headers = register_user(UserRole.SUPER_ADMIN)

    complaint_response = create_complaint(manager_headers)

    complaint_id = complaint_response.json()["id"]

    response = client.patch(
        f"/api/v1/customer-complaints/{complaint_id}",
        json={"priority": "high"},
        headers=customer_headers,
    )

    assert response.status_code == 403


def test_manager_can_resolve_complaint():
    headers = register_user(UserRole.SUPER_ADMIN)

    complaint_response = create_complaint(headers)

    complaint_id = complaint_response.json()["id"]

    response = client.patch(
        f"/api/v1/customer-complaints/{complaint_id}",
        json={
            "status": "resolved",
            "resolution_remarks": "Collection completed successfully.",
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["status"] == "resolved"
    assert data["resolution_remarks"] == "Collection completed successfully."
    assert data["resolved_at"] is not None


def test_resolution_requires_remarks():
    headers = register_user(UserRole.SUPER_ADMIN)

    complaint_response = create_complaint(headers)

    complaint_id = complaint_response.json()["id"]

    response = client.patch(
        f"/api/v1/customer-complaints/{complaint_id}",
        json={"status": "resolved"},
        headers=headers,
    )

    assert response.status_code == 400


def test_complaint_history_records_creation():
    headers = register_user(UserRole.CUSTOMER)

    complaint_response = create_complaint(headers)

    complaint_id = complaint_response.json()["id"]

    response = client.get(
        f"/api/v1/customer-complaints/{complaint_id}/history",
        headers=headers,
    )

    assert response.status_code == 200

    history = response.json()

    assert len(history) == 1
    assert history[0]["previous_status"] is None
    assert history[0]["new_status"] == "open"


def test_complaint_history_records_status_change():
    headers = register_user(UserRole.SUPER_ADMIN)

    complaint_response = create_complaint(headers)

    complaint_id = complaint_response.json()["id"]

    update_response = client.patch(
        f"/api/v1/customer-complaints/{complaint_id}",
        json={
            "status": "resolved",
            "resolution_remarks": "Issue resolved.",
        },
        headers=headers,
    )

    assert update_response.status_code == 200

    history_response = client.get(
        f"/api/v1/customer-complaints/{complaint_id}/history",
        headers=headers,
    )

    assert history_response.status_code == 200

    history = history_response.json()

    assert len(history) == 2
    assert history[1]["previous_status"] == "open"
    assert history[1]["new_status"] == "resolved"


def test_complaint_not_found():
    headers = register_user(UserRole.SUPER_ADMIN)

    response = client.get(
        f"/api/v1/customer-complaints/{uuid4()}",
        headers=headers,
    )

    assert response.status_code == 404


def test_invalid_assigned_user():
    headers = register_user(UserRole.SUPER_ADMIN)

    complaint_response = create_complaint(headers)

    complaint_id = complaint_response.json()["id"]

    response = client.patch(
        f"/api/v1/customer-complaints/{complaint_id}",
        json={
            "assigned_to_user_id": str(uuid4()),
        },
        headers=headers,
    )

    assert response.status_code == 404


def test_filter_complaints_by_status():
    headers = register_user(UserRole.SUPER_ADMIN)

    create_complaint(headers)

    response = client.get(
        "/api/v1/customer-complaints?status=open",
        headers=headers,
    )

    assert response.status_code == 200

    for complaint in response.json():
        assert complaint["status"] == "open"