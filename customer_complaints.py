from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.session import get_db
from models.user import User

from core.constants import (
    UserRole,
    ComplaintCategory,
    ComplaintPriority,
    ComplaintStatus,
)
from core.permissions import require_roles

from schemas.customer_complaint import (
    CustomerComplaintCreate,
    CustomerComplaintUpdate,
    CustomerComplaintResponse,
    ComplaintHistoryResponse,
)

from services.customer_complaint_service import CustomerComplaintService


router = APIRouter(
    prefix="/api/v1/customer-complaints",
    tags=["Customer Complaints"],
)


MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
]

CREATE_ROLES = MANAGEMENT_ROLES + [UserRole.CUSTOMER]


@router.post(
    "",
    response_model=CustomerComplaintResponse,
    status_code=201,
)
def create_complaint(
    payload: CustomerComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*CREATE_ROLES)),
):
    return CustomerComplaintService.create_complaint(
        db,
        payload,
        current_user,
    )


@router.get(
    "",
    response_model=list[CustomerComplaintResponse],
)
def list_complaints(
    complaint_status: ComplaintStatus | None = Query(
        default=None,
        alias="status",
    ),
    priority: ComplaintPriority | None = None,
    category: ComplaintCategory | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*CREATE_ROLES)),
):
    return CustomerComplaintService.list_complaints(
        db,
        current_user,
        complaint_status=complaint_status,
        priority=priority,
        category=category,
    )


@router.get(
    "/{complaint_id}/history",
    response_model=list[ComplaintHistoryResponse],
)
def get_complaint_history(
    complaint_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*CREATE_ROLES)),
):
    return CustomerComplaintService.get_complaint_history(
        db,
        complaint_id,
        current_user,
    )


@router.get(
    "/{complaint_id}",
    response_model=CustomerComplaintResponse,
)
def get_complaint(
    complaint_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*CREATE_ROLES)),
):
    return CustomerComplaintService.get_complaint(
        db,
        complaint_id,
        current_user,
    )


@router.patch(
    "/{complaint_id}",
    response_model=CustomerComplaintResponse,
)
def update_complaint(
    complaint_id: UUID,
    payload: CustomerComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return CustomerComplaintService.update_complaint(
        db,
        complaint_id,
        payload,
        current_user,
    )