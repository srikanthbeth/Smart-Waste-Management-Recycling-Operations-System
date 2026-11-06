
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.constants import (
    LocationStatus,
    LocationType,
    UserRole,
)
from core.permissions import require_roles
from db.session import get_db
from schemas.location import (
    LocationCreate,
    LocationResponse,
    LocationStatusUpdate,
    LocationUpdate,
)
from services.location_service import LocationService


router = APIRouter(
    prefix="/api/v1/locations",
    tags=["Locations"],
)


MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
]

VIEW_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
    UserRole.DRIVER,
    UserRole.RECYCLING_CENTER_MANAGER,
    UserRole.FIELD_WORKER,
    UserRole.CUSTOMER,
]


@router.post(
    "",
    response_model=LocationResponse,
    status_code=201,
)
def create_location(
    payload: LocationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return LocationService.create_location(
        db,
        payload.model_dump(),
    )


@router.get(
    "",
    response_model=list[LocationResponse],
)
def list_locations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    location_type: LocationType | None = None,
    status_filter: LocationStatus | None = Query(
        default=None,
        alias="status",
    ),
    parent_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*VIEW_ROLES)),
):
    return LocationService.list_locations(
        db=db,
        skip=skip,
        limit=limit,
        location_type=location_type,
        status_filter=status_filter,
        parent_id=parent_id,
    )


@router.get(
    "/{location_id}",
    response_model=LocationResponse,
)
def get_location(
    location_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*VIEW_ROLES)),
):
    return LocationService.get_location(db, location_id)


@router.patch(
    "/{location_id}",
    response_model=LocationResponse,
)
def update_location(
    location_id: UUID,
    payload: LocationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return LocationService.update_location(
        db,
        location_id,
        payload.model_dump(exclude_unset=True),
    )


@router.patch(
    "/{location_id}/status",
    response_model=LocationResponse,
)
def update_location_status(
    location_id: UUID,
    payload: LocationStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return LocationService.update_location_status(
        db,
        location_id,
        payload.status,
    )
