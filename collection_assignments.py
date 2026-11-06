from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.session import get_db

from core.constants import (
    UserRole,
    AssignmentStatus,
)

from core.permissions import require_roles

from models.user import User

from routes.auth import get_current_user

from schemas.collection_assignment import (
    CollectionAssignmentCreate,
    CollectionAssignmentUpdate,
    CollectionAssignmentStatusUpdate,
    CollectionAssignmentResponse,
)

from services.collection_assignment_service import (
    CollectionAssignmentService,
)


router = APIRouter(
    prefix="/api/v1/collection-assignments",
    tags=["Collection Assignments"],
)


MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
]


@router.post(
    "",
    response_model=CollectionAssignmentResponse,
    status_code=201,
)
def create_collection_assignment(
    data: CollectionAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionAssignmentService.create_assignment(
        db=db,
        data=data,
        assigned_by_user_id=current_user.id,
    )


@router.get(
    "",
    response_model=list[CollectionAssignmentResponse],
)
def list_collection_assignments(
    assignment_status: Optional[AssignmentStatus] = Query(
        default=None,
        alias="status",
    ),
    driver_id: Optional[UUID] = None,
    vehicle_id: Optional[UUID] = None,
    pickup_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionAssignmentService.list_assignments(
        db=db,
        status_filter=assignment_status,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        pickup_id=pickup_id,
    )


@router.get(
    "/pickup/{pickup_id}/history",
    response_model=list[CollectionAssignmentResponse],
)
def get_pickup_assignment_history(
    pickup_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionAssignmentService.get_pickup_assignment_history(
        db=db,
        pickup_id=pickup_id,
    )


@router.get(
    "/{assignment_id}",
    response_model=CollectionAssignmentResponse,
)
def get_collection_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionAssignmentService.get_assignment(
        db=db,
        assignment_id=assignment_id,
    )


@router.patch(
    "/{assignment_id}",
    response_model=CollectionAssignmentResponse,
)
def update_collection_assignment(
    assignment_id: UUID,
    data: CollectionAssignmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionAssignmentService.update_assignment(
        db=db,
        assignment_id=assignment_id,
        data=data,
    )


@router.patch(
    "/{assignment_id}/status",
    response_model=CollectionAssignmentResponse,
)
def update_collection_assignment_status(
    assignment_id: UUID,
    data: CollectionAssignmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CollectionAssignmentService.update_assignment_status(
        db=db,
        assignment_id=assignment_id,
        data=data,
    )