
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import UserRole, StaffStatus, StaffAvailability
from core.permissions import require_roles
from db.session import get_db

from schemas.driver import (
    DriverCreate,
    DriverUpdate,
    DriverStatusUpdate,
    DriverResponse,
)
from services.driver_service import DriverService


router = APIRouter(
    prefix="/api/v1/drivers",
    tags=["Drivers"],
)


management_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
)

driver_access_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
    UserRole.DRIVER,
)


@router.post(
    "",
    response_model=DriverResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_driver(
    data: DriverCreate,
    db: Session = Depends(get_db),
    current_user=Depends(management_roles),
):
    return DriverService.create_driver(db, data)


@router.get(
    "/me",
    response_model=DriverResponse,
)
def get_my_driver_profile(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.DRIVER)),
):
    return DriverService.get_my_profile(db, current_user.id)


@router.get(
    "",
    response_model=list[DriverResponse],
)
def list_drivers(
    status_filter: StaffStatus | None = Query(default=None, alias="status"),
    availability: StaffAvailability | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(management_roles),
):
    return DriverService.list_drivers(
        db,
        status_filter=status_filter,
        availability=availability,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{driver_id}",
    response_model=DriverResponse,
)
def get_driver(
    driver_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(driver_access_roles),
):
    driver = DriverService.get_driver(db, driver_id)

    if (
        current_user.role == UserRole.DRIVER
        and driver.user_id != current_user.id
    ):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own driver profile",
        )

    return driver


@router.patch(
    "/{driver_id}",
    response_model=DriverResponse,
)
def update_driver(
    driver_id: UUID,
    data: DriverUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(management_roles),
):
    return DriverService.update_driver(db, driver_id, data)


@router.patch(
    "/{driver_id}/status",
    response_model=DriverResponse,
)
def update_driver_status(
    driver_id: UUID,
    data: DriverStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(management_roles),
):
    return DriverService.update_status(db, driver_id, data)
