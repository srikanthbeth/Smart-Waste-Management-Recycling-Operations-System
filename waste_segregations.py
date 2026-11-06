from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from core.constants import UserRole, WasteSegregationStatus
from core.permissions import require_roles

from models.user import User

from routes.auth import get_current_user

from schemas.waste_segregation import (
    WasteSegregationCreate,
    WasteSegregationUpdate,
    WasteSegregationResponse,
)

from services.waste_segregation_service import (
    WasteSegregationService,
)


router = APIRouter(
    prefix="/api/v1/waste-segregations",
    tags=["Waste Segregation"],
)


SEGREGATION_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
    UserRole.RECYCLING_CENTER_MANAGER,
    UserRole.FIELD_WORKER,
]


@router.post(
    "/",
    response_model=WasteSegregationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_segregation(
    payload: WasteSegregationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*SEGREGATION_ROLES)
    ),
):
    return WasteSegregationService.create_segregation(
        db,
        payload,
        current_user,
    )


@router.get(
    "/",
    response_model=list[WasteSegregationResponse],
)
def list_segregations(
    recycling_center_id: UUID | None = None,
    transfer_id: UUID | None = None,
    waste_category_id: UUID | None = None,
    segregation_status: WasteSegregationStatus | None = None,
    segregated_by_user_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*SEGREGATION_ROLES)
    ),
):
    return WasteSegregationService.list_segregations(
        db=db,
        recycling_center_id=recycling_center_id,
        transfer_id=transfer_id,
        waste_category_id=waste_category_id,
        segregation_status=segregation_status,
        segregated_by_user_id=segregated_by_user_id,
    )


@router.get(
    "/transfer/{transfer_id}/history",
    response_model=list[WasteSegregationResponse],
)
def get_transfer_segregation_history(
    transfer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*SEGREGATION_ROLES)
    ),
):
    return WasteSegregationService.get_transfer_history(
        db,
        transfer_id,
    )


@router.get(
    "/{segregation_id}",
    response_model=WasteSegregationResponse,
)
def get_segregation(
    segregation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*SEGREGATION_ROLES)
    ),
):
    return WasteSegregationService.get_segregation(
        db,
        segregation_id,
    )


@router.patch(
    "/{segregation_id}",
    response_model=WasteSegregationResponse,
)
def update_segregation(
    segregation_id: UUID,
    payload: WasteSegregationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*SEGREGATION_ROLES)
    ),
):
    return WasteSegregationService.update_segregation(
        db,
        segregation_id,
        payload,
    )