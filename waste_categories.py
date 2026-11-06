from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import UserRole, WasteCategoryStatus
from core.permissions import require_roles
from db.session import get_db
from routes.auth import get_current_user
from schemas.waste_category import (
    WasteCategoryCreate,
    WasteCategoryResponse,
    WasteCategoryStatusUpdate,
    WasteCategoryUpdate,
)
from services.waste_category_service import WasteCategoryService


router = APIRouter(
    prefix="/api/v1/waste-categories",
    tags=["Waste Categories"],
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
    response_model=WasteCategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_waste_category(
    category_data: WasteCategoryCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return WasteCategoryService.create_category(
        db,
        category_data,
    )


@router.get(
    "",
    response_model=list[WasteCategoryResponse],
)
def list_waste_categories(
    category_status: WasteCategoryStatus | None = Query(
        default=None,
        alias="status",
    ),
    is_recyclable: bool | None = None,
    is_hazardous: bool | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*VIEW_ROLES)),
):
    return WasteCategoryService.list_categories(
        db,
        category_status,
        is_recyclable,
        is_hazardous,
    )


@router.get(
    "/{category_id}",
    response_model=WasteCategoryResponse,
)
def get_waste_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*VIEW_ROLES)),
):
    return WasteCategoryService.get_category(
        db,
        category_id,
    )


@router.patch(
    "/{category_id}",
    response_model=WasteCategoryResponse,
)
def update_waste_category(
    category_id: UUID,
    update_data: WasteCategoryUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return WasteCategoryService.update_category(
        db,
        category_id,
        update_data,
    )


@router.patch(
    "/{category_id}/status",
    response_model=WasteCategoryResponse,
)
def update_waste_category_status(
    category_id: UUID,
    status_data: WasteCategoryStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return WasteCategoryService.update_category_status(
        db,
        category_id,
        status_data.status,
    )