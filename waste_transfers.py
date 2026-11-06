
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from db.session import get_db
from core.constants import UserRole, WasteTransferStatus

from models.user import User

from schemas.waste_transfer import (
    WasteTransferCreate,
    WasteTransferUpdate,
    WasteTransferResponse,
    WasteTransferDispatch,
    WasteTransferReceive,
)

from services.waste_transfer_service import WasteTransferService
from core.permissions import require_roles
from routes.auth import get_current_user


router = APIRouter(
    prefix="/api/v1/waste-transfers",
    tags=["Waste Transfers"],
)

MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
]

RECEIVING_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.RECYCLING_CENTER_MANAGER,
]


@router.post(
    "/",
    response_model=WasteTransferResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transfer(
    payload: WasteTransferCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
):
    return WasteTransferService.create_transfer(
        db,
        payload.model_dump(),
        current_user,
    )


@router.get(
    "/",
    response_model=list[WasteTransferResponse],
)
def list_transfers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    recycling_center_id: UUID | None = None,
    pickup_id: UUID | None = None,
    transfer_status: WasteTransferStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            *MANAGEMENT_ROLES,
            UserRole.RECYCLING_CENTER_MANAGER,
        )
    ),
):
    return WasteTransferService.list_transfers(
        db=db,
        skip=skip,
        limit=limit,
        recycling_center_id=recycling_center_id,
        pickup_id=pickup_id,
        transfer_status=transfer_status,
        created_by_user_id=None,
    )

@router.get(
    "/{transfer_id}",
    response_model=WasteTransferResponse,
)
def get_transfer(
    transfer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transfer = WasteTransferService.get_transfer(
        db,
        transfer_id,
    )

    if (
        current_user.role not in MANAGEMENT_ROLES
        and current_user.role != UserRole.RECYCLING_CENTER_MANAGER
        and transfer.created_by_user_id != current_user.id
    ):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to view this transfer",
        )

    return transfer


@router.patch(
    "/{transfer_id}",
    response_model=WasteTransferResponse,
)
def update_transfer(
    transfer_id: UUID,
    payload: WasteTransferUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
):
    return WasteTransferService.update_transfer(
        db,
        transfer_id,
        payload.model_dump(exclude_unset=True),
    )


@router.post(
    "/{transfer_id}/dispatch",
    response_model=WasteTransferResponse,
)
def dispatch_transfer(
    transfer_id: UUID,
    payload: WasteTransferDispatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
):
    return WasteTransferService.dispatch_transfer(
        db,
        transfer_id,
        payload.remarks,
    )


@router.post(
    "/{transfer_id}/in-transit",
    response_model=WasteTransferResponse,
)
def mark_in_transit(
    transfer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
):
    return WasteTransferService.mark_in_transit(
        db,
        transfer_id,
    )


@router.post(
    "/{transfer_id}/receive",
    response_model=WasteTransferResponse,
)
def receive_transfer(
    transfer_id: UUID,
    payload: WasteTransferReceive,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*RECEIVING_ROLES)
    ),
):
    return WasteTransferService.receive_transfer(
        db,
        transfer_id,
        payload.received_quantity_kg,
        current_user,
        payload.remarks,
    )


@router.post(
    "/{transfer_id}/reject",
    response_model=WasteTransferResponse,
)
def reject_transfer(
    transfer_id: UUID,
    payload: WasteTransferDispatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*RECEIVING_ROLES)
    ),
):
    return WasteTransferService.reject_transfer(
        db,
        transfer_id,
        payload.remarks,
    )


@router.post(
    "/{transfer_id}/cancel",
    response_model=WasteTransferResponse,
)
def cancel_transfer(
    transfer_id: UUID,
    payload: WasteTransferDispatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(*MANAGEMENT_ROLES)
    ),
):
    return WasteTransferService.cancel_transfer(
        db,
        transfer_id,
        payload.remarks,
    )
