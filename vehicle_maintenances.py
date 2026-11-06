from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.session import get_db
from models.user import User
from core.constants import (
    UserRole,
    MaintenanceType,
    MaintenanceStatus,
    MaintenancePriority,
)
from core.permissions import require_roles

from schemas.vehicle_maintenance import (
    VehicleMaintenanceCreate,
    VehicleMaintenanceUpdate,
    VehicleMaintenanceResponse,
)

from services.vehicle_maintenance_service import VehicleMaintenanceService


router = APIRouter(
    prefix="/api/v1/vehicle-maintenances",
    tags=["Vehicle Maintenance"],
)


MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
]


@router.post(
    "",
    response_model=VehicleMaintenanceResponse,
    status_code=201,
)
def create_maintenance(
    payload: VehicleMaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return VehicleMaintenanceService.create_maintenance(
        db, payload, current_user
    )


@router.get("", response_model=list[VehicleMaintenanceResponse])
def list_maintenance(
    vehicle_id: UUID | None = None,
    maintenance_type: MaintenanceType | None = None,
    maintenance_status: MaintenanceStatus | None = Query(
        default=None,
        alias="status",
    ),
    priority: MaintenancePriority | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return VehicleMaintenanceService.list_maintenance(
        db,
        vehicle_id=vehicle_id,
        maintenance_type=maintenance_type,
        status=maintenance_status,
        priority=priority,
    )


@router.get(
    "/vehicle/{vehicle_id}/history",
    response_model=list[VehicleMaintenanceResponse],
)
def get_vehicle_maintenance_history(
    vehicle_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return VehicleMaintenanceService.get_vehicle_history(db, vehicle_id)


@router.get(
    "/{maintenance_id}",
    response_model=VehicleMaintenanceResponse,
)
def get_maintenance(
    maintenance_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return VehicleMaintenanceService.get_maintenance(db, maintenance_id)


@router.patch(
    "/{maintenance_id}",
    response_model=VehicleMaintenanceResponse,
)
def update_maintenance(
    maintenance_id: UUID,
    payload: VehicleMaintenanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return VehicleMaintenanceService.update_maintenance(
        db, maintenance_id, payload
    )