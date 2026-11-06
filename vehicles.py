from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.session import get_db
from core.constants import (
    UserRole,
    VehicleStatus,
    VehicleType,
)
from core.permissions import require_roles
from schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleStatusUpdate,
    VehicleResponse,
)
from services import vehicle_service


router = APIRouter(
    prefix="/api/v1/vehicles",
    tags=["Vehicle Management"],
)

vehicle_manager = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
)


@router.post(
    "",
    response_model=VehicleResponse,
    status_code=201,
    dependencies=[Depends(vehicle_manager)],
)
def create_vehicle(
    payload: VehicleCreate,
    db: Session = Depends(get_db),
):
    return vehicle_service.create_vehicle(
        db,
        payload.model_dump(),
    )


@router.get(
    "",
    response_model=list[VehicleResponse],
    dependencies=[Depends(vehicle_manager)],
)
def list_vehicles(
    status_filter: VehicleStatus | None = Query(
        default=None,
        alias="status",
    ),
    vehicle_type: VehicleType | None = None,
    location_id: UUID | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return vehicle_service.list_vehicles(
        db=db,
        status_filter=status_filter,
        vehicle_type=vehicle_type,
        location_id=location_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    dependencies=[Depends(vehicle_manager)],
)
def get_vehicle(
    vehicle_id: UUID,
    db: Session = Depends(get_db),
):
    return vehicle_service.get_vehicle(db, vehicle_id)


@router.patch(
    "/{vehicle_id}",
    response_model=VehicleResponse,
    dependencies=[Depends(vehicle_manager)],
)
def update_vehicle(
    vehicle_id: UUID,
    payload: VehicleUpdate,
    db: Session = Depends(get_db),
):
    return vehicle_service.update_vehicle(
        db,
        vehicle_id,
        payload.model_dump(exclude_unset=True),
    )


@router.patch(
    "/{vehicle_id}/status",
    response_model=VehicleResponse,
    dependencies=[Depends(vehicle_manager)],
)
def update_vehicle_status(
    vehicle_id: UUID,
    payload: VehicleStatusUpdate,
    db: Session = Depends(get_db),
):
    return vehicle_service.update_vehicle_status(
        db,
        vehicle_id,
        payload.status,
    )