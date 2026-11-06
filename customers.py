
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import (
    CustomerStatus,
    CustomerType,
    UserRole,
)
from core.permissions import require_roles
from db.session import get_db
from routes.auth import get_current_user
from schemas.customer import (
    CustomerCreate,
    CustomerResponse,
    CustomerStatusUpdate,
    CustomerUpdate,
)
from services.customer_service import CustomerService


router = APIRouter(
    prefix="/api/v1/customers",
    tags=["Customers"],
)


MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
]

PROFILE_ACCESS_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
    UserRole.CUSTOMER,
]


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.CUSTOMER)
    ),
):
    return CustomerService.create_customer(
        db,
        current_user,
        customer_data,
    )


@router.get(
    "/me",
    response_model=CustomerResponse,
)
def get_my_customer_profile(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.CUSTOMER)
    ),
):
    return CustomerService.get_my_customer_profile(
        db,
        current_user,
    )


@router.get(
    "",
    response_model=list[CustomerResponse],
)
def list_customers(
    customer_type: CustomerType | None = Query(default=None),
    customer_status: CustomerStatus | None = Query(
        default=None,
        alias="status",
    ),
    location_id: UUID | None = Query(default=None),
    city: str | None = Query(default=None, min_length=2),
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
):
    return CustomerService.list_customers(
        db,
        customer_type=customer_type,
        customer_status=customer_status,
        location_id=location_id,
        city=city,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(*PROFILE_ACCESS_ROLES)
    ),
):
    return CustomerService.get_customer_for_user(
        db,
        customer_id,
        current_user,
    )


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
)
def update_customer(
    customer_id: UUID,
    update_data: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(*PROFILE_ACCESS_ROLES)
    ),
):
    return CustomerService.update_customer(
        db,
        customer_id,
        current_user,
        update_data,
    )


@router.patch(
    "/{customer_id}/status",
    response_model=CustomerResponse,
)
def update_customer_status(
    customer_id: UUID,
    status_data: CustomerStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
):
    return CustomerService.update_customer_status(
        db,
        customer_id,
        status_data.status,
    )
