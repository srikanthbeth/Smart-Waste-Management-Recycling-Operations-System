
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import PickupStatus, UserRole
from core.permissions import require_roles
from db.session import get_db
from routes.auth import get_current_user
from schemas.pickup import (
    PickupCreate,
    PickupResponse,
    PickupStatusUpdate,
    PickupUpdate,
)
from services.pickup_service import PickupService


router = APIRouter(
    prefix="/api/v1/pickups",
    tags=["Pickups"],
)


MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
]

PICKUP_ACCESS_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
    UserRole.CUSTOMER,
]


@router.post(
    "",
    response_model=PickupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_pickup(
    pickup_data: PickupCreate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.CUSTOMER)
    ),
):
    return PickupService.create_pickup(
        db,
        current_user,
        pickup_data,
    )


@router.get(
    "/me",
    response_model=list[PickupResponse],
)
def list_my_pickups(
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.CUSTOMER)
    ),
):
    return PickupService.list_my_pickups(
        db,
        current_user,
    )


@router.get(
    "",
    response_model=list[PickupResponse],
)
def list_pickups(
    pickup_status: PickupStatus | None = Query(
        default=None,
        alias="status",
    ),
    location_id: UUID | None = Query(default=None),
    preferred_date: date | None = Query(default=None),
    city: str | None = Query(default=None, min_length=2),
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
):
    return PickupService.list_pickups(
        db,
        current_user,
        pickup_status=pickup_status,
        location_id=location_id,
        preferred_date=preferred_date,
        city=city,
    )


@router.get(
    "/{pickup_id}",
    response_model=PickupResponse,
)
def get_pickup(
    pickup_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(*PICKUP_ACCESS_ROLES)
    ),
):
    return PickupService.get_pickup_for_user(
        db,
        pickup_id,
        current_user,
    )


@router.patch(
    "/{pickup_id}",
    response_model=PickupResponse,
)
def update_pickup(
    pickup_id: UUID,
    update_data: PickupUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(UserRole.CUSTOMER)
    ),
):
    return PickupService.update_pickup(
        db,
        pickup_id,
        current_user,
        update_data,
    )


@router.patch(
    "/{pickup_id}/status",
    response_model=PickupResponse,
)
def update_pickup_status(
    pickup_id: UUID,
    status_data: PickupStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(*PICKUP_ACCESS_ROLES)
    ),
):
    return PickupService.update_pickup_status(
        db,
        pickup_id,
        current_user,
        status_data,
    )
