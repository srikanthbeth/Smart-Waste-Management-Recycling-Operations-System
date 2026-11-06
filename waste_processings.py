
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from db.session import get_db
from core.constants import (
    UserRole,
    WasteProcessingStatus,
    WasteProcessingMethod,
)
from core.permissions import require_roles

from models.user import User

from schemas.waste_processing import (
    WasteProcessingCreate,
    WasteProcessingResponse,
)

from services.waste_processing_service import (
    WasteProcessingService,
)


router = APIRouter(
    prefix="/api/v1/waste-processings",
    tags=["Waste Processing"],
)


PROCESSING_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
    UserRole.RECYCLING_CENTER_MANAGER,
    UserRole.FIELD_WORKER,
]


@router.post(
    "/",
    response_model=WasteProcessingResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_processing(
    payload: WasteProcessingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*PROCESSING_ROLES)
    ),
):
    return WasteProcessingService.create_processing(
        db,
        payload,
        current_user,
    )


@router.get(
    "/",
    response_model=list[WasteProcessingResponse],
)
def list_processings(
    segregation_id: UUID | None = None,
    recycling_center_id: UUID | None = None,
    waste_category_id: UUID | None = None,
    processing_status: WasteProcessingStatus | None = None,
    processing_method: WasteProcessingMethod | None = None,
    processed_by_user_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*PROCESSING_ROLES)
    ),
):
    return WasteProcessingService.list_processings(
        db=db,
        segregation_id=segregation_id,
        recycling_center_id=recycling_center_id,
        waste_category_id=waste_category_id,
        processing_status=processing_status,
        processing_method=processing_method,
        processed_by_user_id=processed_by_user_id,
    )


@router.get(
    "/segregation/{segregation_id}/history",
    response_model=list[WasteProcessingResponse],
)
def get_segregation_processing_history(
    segregation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*PROCESSING_ROLES)
    ),
):
    return WasteProcessingService.get_segregation_history(
        db,
        segregation_id,
    )


@router.get(
    "/{processing_id}",
    response_model=WasteProcessingResponse,
)
def get_processing(
    processing_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*PROCESSING_ROLES)
    ),
):
    return WasteProcessingService.get_processing(
        db,
        processing_id,
    )
