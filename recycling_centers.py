
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from core.constants import UserRole
from core.permissions import require_roles

from routes.auth import get_current_user

from schemas.recycling_center import (
    RecyclingCenterCreate,
    RecyclingCenterUpdate,
    RecyclingCenterStatusUpdate,
    RecyclingCenterResponse,
)

from services.recycling_center_service import (
    RecyclingCenterService,
)


router = APIRouter(
    prefix="/api/v1/recycling-centers",
    tags=["Recycling Centers"],
)


MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
]


@router.post(
    "",
    response_model=RecyclingCenterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_recycling_center(
    center_data: RecyclingCenterCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return RecyclingCenterService.create_center(
        db,
        center_data.model_dump(),
    )


@router.get(
    "",
    response_model=list[RecyclingCenterResponse],
)
def list_recycling_centers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return RecyclingCenterService.list_centers(
        db,
        skip,
        limit,
    )


@router.get(
    "/{center_id}",
    response_model=RecyclingCenterResponse,
)
def get_recycling_center(
    center_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return RecyclingCenterService.get_center(
        db,
        center_id,
    )


@router.patch(
    "/{center_id}",
    response_model=RecyclingCenterResponse,
)
def update_recycling_center(
    center_id: UUID,
    center_data: RecyclingCenterUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    update_data = center_data.model_dump(exclude_unset=True)

    return RecyclingCenterService.update_center(
        db,
        center_id,
        update_data,
    )


@router.patch(
    "/{center_id}/status",
    response_model=RecyclingCenterResponse,
)
def update_recycling_center_status(
    center_id: UUID,
    status_data: RecyclingCenterStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return RecyclingCenterService.update_center_status(
        db,
        center_id,
        status_data.status,
        status_data.is_available,
    )


@router.delete(
    "/{center_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_recycling_center(
    center_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    RecyclingCenterService.delete_center(
        db,
        center_id,
    )

    return None
