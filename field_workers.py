
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from core.constants import UserRole, StaffStatus, StaffAvailability
from core.permissions import require_roles
from db.session import get_db

from schemas.field_worker import (
    FieldWorkerCreate,
    FieldWorkerUpdate,
    FieldWorkerStatusUpdate,
    FieldWorkerResponse,
)
from services.field_worker_service import FieldWorkerService


router = APIRouter(
    prefix="/api/v1/field-workers",
    tags=["Field Workers"],
)


management_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
)

worker_access_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
    UserRole.FIELD_WORKER,
)


@router.post(
    "",
    response_model=FieldWorkerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_field_worker(
    data: FieldWorkerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(management_roles),
):
    return FieldWorkerService.create_worker(db, data)


@router.get(
    "/me",
    response_model=FieldWorkerResponse,
)
def get_my_field_worker_profile(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(UserRole.FIELD_WORKER)),
):
    return FieldWorkerService.get_my_profile(db, current_user.id)


@router.get(
    "",
    response_model=list[FieldWorkerResponse],
)
def list_field_workers(
    status_filter: StaffStatus | None = Query(default=None, alias="status"),
    availability: StaffAvailability | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(management_roles),
):
    return FieldWorkerService.list_workers(
        db,
        status_filter=status_filter,
        availability=availability,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{worker_id}",
    response_model=FieldWorkerResponse,
)
def get_field_worker(
    worker_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(worker_access_roles),
):
    worker = FieldWorkerService.get_worker(db, worker_id)

    if (
        current_user.role == UserRole.FIELD_WORKER
        and worker.user_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own field worker profile",
        )

    return worker


@router.patch(
    "/{worker_id}",
    response_model=FieldWorkerResponse,
)
def update_field_worker(
    worker_id: UUID,
    data: FieldWorkerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(management_roles),
):
    return FieldWorkerService.update_worker(db, worker_id, data)


@router.patch(
    "/{worker_id}/status",
    response_model=FieldWorkerResponse,
)
def update_field_worker_status(
    worker_id: UUID,
    data: FieldWorkerStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(management_roles),
):
    return FieldWorkerService.update_status(db, worker_id, data)
