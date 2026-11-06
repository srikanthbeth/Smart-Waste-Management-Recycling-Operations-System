
import os
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()

os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:Srik8499@localhost:5433/smart_waste_management_test",
)
os.environ["ENVIRONMENT"] = "development"

from fastapi.testclient import TestClient
from sqlalchemy import text

from db.session import SessionLocal, engine
from main import app
from models.user import User
from core.constants import UserRole
from core.security import hash_password


client = TestClient(app)


def unique_email():
    return f"user_{uuid4().hex[:10]}@example.com"


def cleanup_database():
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                TRUNCATE TABLE
                    password_reset_tokens,
                    users
                RESTART IDENTITY CASCADE
                """
            )
        )


def setup_module():
    # Tables are created and managed by Alembic.
    # Do not call Base.metadata.create_all() here.
    cleanup_database()


def teardown_module():
    cleanup_database()


def register_user(email=None, password="StrongPassword123!"):
    if email is None:
        email = unique_email()

    return client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Customer",
            "email": email,
            "password": password,
            "phone_number": "9876543210",
        },
    )


def login_user(email, password="StrongPassword123!"):
    return client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )


def create_admin():
    email = unique_email()
    db = SessionLocal()

    try:
        admin = User(
            full_name="Test Super Admin",
            email=email,
            hashed_password=hash_password("AdminPassword123!"),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
        )

        db.add(admin)
        db.commit()
    finally:
        db.close()

    response = login_user(email, "AdminPassword123!")
    assert response.status_code == 200, response.text

    return response.json()["access_token"]


def create_user_directly(email=None, role=UserRole.CUSTOMER):
    email = email or unique_email()
    db = SessionLocal()

    try:
        user = User(
            full_name="Test User",
            email=email,
            hashed_password=hash_password("StrongPassword123!"),
            role=role,
            is_active=True,
            is_verified=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return str(user.id)
    finally:
        db.close()


def test_register_user():
    response = register_user()

    assert response.status_code == 201, response.text

    data = response.json()

    assert data["full_name"] == "Test Customer"
    assert data["email"].endswith("@example.com")
    assert data["role"] == "customer"
    assert data["is_active"] is True


def test_public_registration_cannot_select_admin_role():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Attempted Admin",
            "email": unique_email(),
            "password": "StrongPassword123!",
            "role": "super_admin",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "customer"


def test_duplicate_email():
    email = unique_email()

    first = register_user(email)
    assert first.status_code == 201, first.text

    second = register_user(email)

    assert second.status_code == 409


def test_email_is_normalized():
    email = unique_email().upper()

    response = register_user(email)

    assert response.status_code == 201, response.text
    assert response.json()["email"] == email.lower()


def test_password_is_hashed():
    email = unique_email()

    response = register_user(email)
    assert response.status_code == 201, response.text

    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.email == email.lower()
        ).first()

        assert user is not None
        assert user.hashed_password != "StrongPassword123!"
    finally:
        db.close()


def test_weak_password_rejected():
    response = register_user(
        password="weak"
    )

    assert response.status_code == 422


def test_login_success():
    email = unique_email()

    register_response = register_user(email)
    assert register_response.status_code == 201

    response = login_user(email)

    assert response.status_code == 200, response.text

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_invalid_password():
    email = unique_email()

    register_user(email)

    response = login_user(
        email,
        "WrongPassword123!",
    )

    assert response.status_code == 401


def test_login_unknown_email():
    response = login_user(unique_email())

    assert response.status_code == 401


def test_current_user():
    email = unique_email()

    register_user(email)

    login_response = login_user(email)
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["email"] == email.lower()
    assert response.json()["role"] == "customer"


def test_missing_authentication():
    response = client.get("/api/v1/auth/me")

    assert response.status_code in (401, 403)


def test_invalid_access_token():
    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401


def test_refresh_token():
    email = unique_email()

    register_user(email)

    login_response = login_user(email)
    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": refresh_token
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["refresh_token"] != refresh_token


def test_old_refresh_token_cannot_be_reused():
    email = unique_email()

    register_user(email)

    login_response = login_user(email)
    assert login_response.status_code == 200

    old_refresh_token = login_response.json()["refresh_token"]

    first_refresh = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": old_refresh_token
        },
    )

    assert first_refresh.status_code == 200, first_refresh.text

    second_refresh = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": old_refresh_token
        },
    )

    assert second_refresh.status_code == 401


def test_invalid_refresh_token():
    response = client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": "invalid-refresh-token"
        },
    )

    assert response.status_code == 401


def test_logout():
    email = unique_email()

    register_user(email)

    login_response = login_user(email)
    assert login_response.status_code == 200

    data = login_response.json()

    response = client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": data["refresh_token"]
        },
        headers={
            "Authorization": f"Bearer {data['access_token']}"
        },
    )

    assert response.status_code == 200, response.text

    me_response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {data['access_token']}"
        },
    )

    assert me_response.status_code == 401


def test_password_reset_request():
    email = unique_email()

    register_user(email)

    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "email": email
        },
    )

    assert response.status_code == 200, response.text
    assert response.json().get("reset_token")


def test_password_reset_unknown_email():
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "email": unique_email()
        },
    )

    assert response.status_code == 200


def test_password_reset_changes_password():
    email = unique_email()

    register_user(email)

    reset_response = client.post(
        "/api/v1/auth/password-reset/request",
        json={
            "email": email
        },
    )

    assert reset_response.status_code == 200, reset_response.text

    reset_token = reset_response.json().get("reset_token")
    assert reset_token

    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "new_password": "NewStrongPassword456!",
        },
    )

    assert response.status_code == 200, response.text

    old_login = login_user(
        email,
        "StrongPassword123!",
    )

    assert old_login.status_code == 401

    new_login = login_user(
        email,
        "NewStrongPassword456!",
    )

    assert new_login.status_code == 200, new_login.text


def test_invalid_password_reset_token():
    response = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={
            "token": "invalid-reset-token",
            "new_password": "NewStrongPassword456!",
        },
    )

    assert response.status_code == 400


def test_customer_cannot_update_user_status():
    email = unique_email()

    register_user(email)

    login_response = login_user(email)
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    target_id = create_user_directly()

    response = client.patch(
        f"/api/v1/users/{target_id}/status",
        json={
            "is_active": False
        },
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 403


def test_super_admin_can_update_user_status():
    token = create_admin()

    target_id = create_user_directly()

    response = client.patch(
        f"/api/v1/users/{target_id}/status",
        json={
            "is_active": False
        },
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


def test_inactive_user_cannot_login():
    email = unique_email()

    user_id = create_user_directly(email)

    db = SessionLocal()

    try:
        user = db.get(User, user_id)

        assert user is not None

        user.is_active = False
        db.commit()
    finally:
        db.close()

    response = login_user(email)

    assert response.status_code == 403


def test_super_admin_cannot_deactivate_self():
    token = create_admin()

    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert response.status_code == 200

    admin_id = response.json()["id"]

    deactivate_response = client.patch(
        f"/api/v1/users/{admin_id}/status",
        json={
            "is_active": False
        },
        headers={
            "Authorization": f"Bearer {token}"
        },
    )

    assert deactivate_response.status_code == 400
