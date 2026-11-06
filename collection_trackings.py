
from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from routes.auth import get_current_user
from core.constants import (
    UserRole,
    CollectionTrackingStatus,
)
from core.permissions import require_roles

from schemas.collection_tracking import (
    CollectionTrackingCreate,
    CollectionTrackingUpdate,
    CollectionTrackingStatusUpdate,
    CollectionTrackingResponse,
)

from services.collection_tracking_service import (
    CollectionTrackingService,
)


router = APIRouter(
    prefix="/api/v1/collection-trackings",
    tags=["Collection Tracking"],
)


MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
]


@router.post(
    "",
    response_model=CollectionTrackingResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_collection_tracking(
    data: CollectionTrackingCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return CollectionTrackingService.start_tracking(
        db,
        data,
        current_user,
    )


@router.get(
    "",
    response_model=list[CollectionTrackingResponse],
)
def list_collection_trackings(
    tracking_status: Optional[CollectionTrackingStatus] = Query(None),
    pickup_id: Optional[UUID] = Query(None),
    assignment_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionTrackingService.list_trackings(
        db,
        tracking_status=tracking_status,
        pickup_id=pickup_id,
        assignment_id=assignment_id,
    )


@router.get(
    "/pickup/{pickup_id}/history",
    response_model=list[CollectionTrackingResponse],
)
def get_pickup_tracking_history(
    pickup_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionTrackingService.get_pickup_tracking_history(
        db,
        pickup_id,
    )


@router.get(
    "/{tracking_id}",
    response_model=CollectionTrackingResponse,
)
def get_collection_tracking(
    tracking_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionTrackingService.get_tracking(
        db,
        tracking_id,
    )


@router.patch(
    "/{tracking_id}",
    response_model=CollectionTrackingResponse,
)
def update_collection_tracking(
    tracking_id: UUID,
    data: CollectionTrackingUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return CollectionTrackingService.update_tracking(
        db,
        tracking_id,
        data,
        current_user,
    )


@router.patch(
    "/{tracking_id}/status",
    response_model=CollectionTrackingResponse,
)
def update_collection_tracking_status(
    tracking_id: UUID,
    data: CollectionTrackingStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return CollectionTrackingService.update_tracking_status(
        db,
        tracking_id,
        data,
        current_user,
    )
