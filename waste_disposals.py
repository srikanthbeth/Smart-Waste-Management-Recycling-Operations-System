from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from db.session import get_db

from core.constants import (
    UserRole,
    WasteDisposalMethod,
    WasteDisposalStatus,
)

from core.permissions import require_roles

from models.user import User

from routes.auth import get_current_user

from schemas.waste_disposal import (
    WasteDisposalCreate,
    WasteDisposalResponse,
)

from services.waste_disposal_service import WasteDisposalService


router = APIRouter(
    prefix="/api/v1/waste-disposals",
    tags=["Waste Disposal"],
)


DISPOSAL_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
    UserRole.RECYCLING_CENTER_MANAGER,
]


@router.post(
    "",
    response_model=WasteDisposalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_disposal(
    payload: WasteDisposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*DISPOSAL_ROLES)
    ),
):
    return WasteDisposalService.create_disposal(
        db,
        payload,
        current_user,
    )


@router.get(
    "",
    response_model=list[WasteDisposalResponse],
)
def list_disposals(
    processing_id: UUID | None = Query(default=None),
    recycling_center_id: UUID | None = Query(default=None),
    disposal_method: WasteDisposalMethod | None = Query(default=None),
    disposal_status: WasteDisposalStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*DISPOSAL_ROLES)
    ),
):
    return WasteDisposalService.list_disposals(
        db,
        processing_id=processing_id,
        recycling_center_id=recycling_center_id,
        disposal_method=disposal_method,
        disposal_status=disposal_status,
    )


@router.get(
    "/processing/{processing_id}/history",
    response_model=list[WasteDisposalResponse],
)
def get_processing_disposal_history(
    processing_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*DISPOSAL_ROLES)
    ),
):
    return WasteDisposalService.get_processing_history(
        db,
        processing_id,
    )


@router.get(
    "/{disposal_id}",
    response_model=WasteDisposalResponse,
)
def get_disposal(
    disposal_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*DISPOSAL_ROLES)
    ),
):
    return WasteDisposalService.get_disposal(
        db,
        disposal_id,
    )