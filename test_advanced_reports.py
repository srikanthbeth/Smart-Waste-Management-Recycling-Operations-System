
import os

import os
from dotenv import load_dotenv

load_dotenv()

test_database_url = os.getenv("TEST_DATABASE_URL")

if not test_database_url:
    raise RuntimeError("TEST_DATABASE_URL is missing")

os.environ["DATABASE_URL"] = test_database_url
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ["ENVIRONMENT"] = "development"

from db.session import SessionLocal, get_db
from main import app


client = TestClient(app)

BASE_URL = "/api/v1/advanced-reports"

PASSWORD = "WasteTest@12345"


def unique_email():
    return f"advanced_{uuid4().hex[:12]}@example.com"



def register_user(role="super_admin"):
    email = unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Advanced Reports Tester",
            "email": email,
            "password": PASSWORD,
            "phone_number": "9876543210",
        },
    )

    assert response.status_code in (200, 201), response.text

    db = SessionLocal()

    try:
        db.execute(
            text(
                "UPDATE users SET role = CAST(:role AS user_role) "
                "WHERE email = :email"
            ),
            {
                "role": role,
                "email": email,
            },
        )
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

@pytest.fixture(scope="module", autouse=True)
def setup_module_database():

    db = SessionLocal()

    try:
        yield
    finally:
        db.close()



@pytest.fixture(scope="module")
def admin_headers():
    return register_user("super_admin")


@pytest.fixture(scope="module")
def manager_headers():
    return register_user("operations_manager")


@pytest.fixture(scope="module")
def customer_headers():
    return register_user("customer")

# =========================================================
# REPORT ENDPOINTS
# =========================================================

REPORT_ENDPOINTS = [
    "/daily-collections",
    "/monthly-collections",
    "/zone-performance",
    "/driver-performance",
    "/vehicle-utilization",
    "/waste-categories",
    "/recycling-centers",
    "/recycling-yield",
    "/disposals",
    "/environmental-impact",
]


# =========================================================
# AUTHENTICATION TESTS
# =========================================================

def test_reports_require_authentication():

    for endpoint in REPORT_ENDPOINTS:

        response = client.get(BASE_URL + endpoint)

        assert response.status_code in (401, 403)


def test_customer_cannot_access_reports(customer_headers):

    for endpoint in REPORT_ENDPOINTS:

        response = client.get(
            BASE_URL + endpoint,
            headers=customer_headers,
        )

        assert response.status_code == 403


# =========================================================
# AUTHORIZED ACCESS TESTS
# =========================================================

@pytest.mark.parametrize("endpoint", REPORT_ENDPOINTS)
def test_super_admin_can_access_reports(endpoint, admin_headers):

    response = client.get(
        BASE_URL + endpoint,
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "items" in data
    assert "pagination" in data

    assert isinstance(data["items"], list)

    assert data["pagination"]["page"] == 1
    assert data["pagination"]["page_size"] == 20


@pytest.mark.parametrize("endpoint", REPORT_ENDPOINTS)
def test_operations_manager_can_access_reports(
    endpoint,
    manager_headers,
):

    response = client.get(
        BASE_URL + endpoint,
        headers=manager_headers,
    )

    assert response.status_code == 200, response.text


# =========================================================
# PAGINATION TESTS
# =========================================================

def test_reports_pagination(admin_headers):

    response = client.get(
        f"{BASE_URL}/daily-collections?page=1&page_size=5",
        headers=admin_headers,
    )

    assert response.status_code == 200

    pagination = response.json()["pagination"]

    assert pagination["page"] == 1
    assert pagination["page_size"] == 5
    assert pagination["total"] >= 0
    assert pagination["total_pages"] >= 0


def test_reports_invalid_page(admin_headers):

    response = client.get(
        f"{BASE_URL}/daily-collections?page=0",
        headers=admin_headers,
    )

    assert response.status_code == 422


def test_reports_invalid_page_size(admin_headers):

    response = client.get(
        f"{BASE_URL}/daily-collections?page_size=101",
        headers=admin_headers,
    )

    assert response.status_code == 422


# =========================================================
# DATE FILTER TESTS
# =========================================================

def test_reports_date_filter(admin_headers):

    response = client.get(
        f"{BASE_URL}/daily-collections"
        "?start_date=2026-01-01"
        "&end_date=2026-12-31",
        headers=admin_headers,
    )

    assert response.status_code == 200


def test_reports_invalid_date_range(admin_headers):

    response = client.get(
        f"{BASE_URL}/daily-collections"
        "?start_date=2026-12-31"
        "&end_date=2026-01-01",
        headers=admin_headers,
    )

    assert response.status_code == 422


# =========================================================
# SORTING TESTS
# =========================================================

@pytest.mark.parametrize("endpoint", REPORT_ENDPOINTS)
def test_reports_ascending_sort(endpoint, admin_headers):

    response = client.get(
        BASE_URL + endpoint + "?sort_order=asc",
        headers=admin_headers,
    )

    assert response.status_code == 200


@pytest.mark.parametrize("endpoint", REPORT_ENDPOINTS)
def test_reports_descending_sort(endpoint, admin_headers):

    response = client.get(
        BASE_URL + endpoint + "?sort_order=desc",
        headers=admin_headers,
    )

    assert response.status_code == 200


def test_reports_invalid_sort_order(admin_headers):

    response = client.get(
        f"{BASE_URL}/daily-collections?sort_order=invalid",
        headers=admin_headers,
    )

    assert response.status_code == 422


# =========================================================
# COLLECTION FILTER TESTS
# =========================================================

def test_daily_collection_report_filters(admin_headers):

    response = client.get(
        f"{BASE_URL}/daily-collections"
        "?start_date=2026-01-01"
        "&end_date=2026-12-31"
        "&status=completed",
        headers=admin_headers,
    )

    assert response.status_code == 200


def test_monthly_collection_report_filters(admin_headers):

    response = client.get(
        f"{BASE_URL}/monthly-collections"
        "?start_date=2026-01-01"
        "&end_date=2026-12-31",
        headers=admin_headers,
    )

    assert response.status_code == 200


# =========================================================
# PERFORMANCE REPORT TESTS
# =========================================================

def test_zone_performance_report(admin_headers):

    response = client.get(
        f"{BASE_URL}/zone-performance",
        headers=admin_headers,
    )

    assert response.status_code == 200


def test_driver_performance_report(admin_headers):

    response = client.get(
        f"{BASE_URL}/driver-performance",
        headers=admin_headers,
    )

    assert response.status_code == 200


def test_vehicle_utilization_report(admin_headers):

    response = client.get(
        f"{BASE_URL}/vehicle-utilization",
        headers=admin_headers,
    )

    assert response.status_code == 200


# =========================================================
# WASTE AND RECYCLING REPORT TESTS
# =========================================================

def test_waste_category_report(admin_headers):

    response = client.get(
        f"{BASE_URL}/waste-categories",
        headers=admin_headers,
    )

    assert response.status_code == 200


def test_recycling_center_report(admin_headers):

    response = client.get(
        f"{BASE_URL}/recycling-centers",
        headers=admin_headers,
    )

    assert response.status_code == 200


def test_recycling_yield_report(admin_headers):

    response = client.get(
        f"{BASE_URL}/recycling-yield",
        headers=admin_headers,
    )

    assert response.status_code == 200


# =========================================================
# DISPOSAL AND ENVIRONMENTAL REPORT TESTS
# =========================================================

def test_disposal_report(admin_headers):

    response = client.get(
        f"{BASE_URL}/disposals",
        headers=admin_headers,
    )

    assert response.status_code == 200


def test_environmental_impact_report(admin_headers):

    response = client.get(
        f"{BASE_URL}/environmental-impact",
        headers=admin_headers,
    )

    assert response.status_code == 200


# =========================================================
# RESPONSE STRUCTURE TESTS
# =========================================================

def test_daily_collection_response_structure(admin_headers):

    response = client.get(
        f"{BASE_URL}/daily-collections",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert "pagination" in data

    if data["items"]:

        item = data["items"][0]

        assert "report_date" in item
        assert "total_requests" in item
        assert "completed_collections" in item
        assert "pending_collections" in item
        assert "missed_collections" in item
        assert "total_collected_kg" in item


def test_zone_performance_response_structure(admin_headers):

    response = client.get(
        f"{BASE_URL}/zone-performance",
        headers=admin_headers,
    )

    assert response.status_code == 200

    if response.json()["items"]:

        item = response.json()["items"][0]

        assert "zone_id" in item
        assert "zone_name" in item
        assert "total_pickups" in item
        assert "completed_pickups" in item
        assert "collection_efficiency_percentage" in item


def test_driver_performance_response_structure(admin_headers):

    response = client.get(
        f"{BASE_URL}/driver-performance",
        headers=admin_headers,
    )

    assert response.status_code == 200

    if response.json()["items"]:

        item = response.json()["items"][0]

        assert "driver_id" in item
        assert "driver_name" in item
        assert "total_assignments" in item
        assert "completed_assignments" in item
        assert "completion_percentage" in item


def test_vehicle_utilization_response_structure(admin_headers):

    response = client.get(
        f"{BASE_URL}/vehicle-utilization",
        headers=admin_headers,
    )

    assert response.status_code == 200

    if response.json()["items"]:

        item = response.json()["items"][0]

        assert "vehicle_id" in item
        assert "vehicle_code" in item
        assert "total_assignments" in item
        assert "utilization_percentage" in item
