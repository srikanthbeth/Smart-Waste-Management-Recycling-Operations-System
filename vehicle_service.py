from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import VehicleStatus, LocationStatus
from models.location import Location
from models.vehicle import Vehicle
from repositories import vehicle_repository


def validate_location(db: Session, location_id: UUID | None) -> None:
    if location_id is None:
        return

    location = db.query(Location).filter(
        Location.id == location_id
    ).first()

    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found",
        )

    if (
        location.status != LocationStatus.ACTIVE
        or not location.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle location must be active",
        )


def create_vehicle(db: Session, vehicle_data: dict) -> Vehicle:
    vehicle_code = vehicle_data["vehicle_code"]
    registration_number = vehicle_data["registration_number"]

    if vehicle_repository.get_vehicle_by_code(db, vehicle_code):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle code already exists",
        )

    if vehicle_repository.get_vehicle_by_registration(
        db, registration_number
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vehicle registration number already exists",
        )

    validate_location(db, vehicle_data.get("location_id"))

    return vehicle_repository.create_vehicle(db, vehicle_data)


def get_vehicle(db: Session, vehicle_id: UUID) -> Vehicle:
    vehicle = vehicle_repository.get_vehicle_by_id(db, vehicle_id)

    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found",
        )

    return vehicle


def list_vehicles(
    db: Session,
    status_filter: VehicleStatus | None = None,
    vehicle_type=None,
    location_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Vehicle]:
    return vehicle_repository.list_vehicles(
        db=db,
        status=status_filter,
        vehicle_type=vehicle_type,
        location_id=location_id,
        skip=skip,
        limit=limit,
    )


def update_vehicle(
    db: Session,
    vehicle_id: UUID,
    update_data: dict,
) -> Vehicle:
    vehicle = get_vehicle(db, vehicle_id)

    if vehicle.status == VehicleStatus.RETIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retired vehicles cannot be updated",
        )

    new_code = update_data.get("vehicle_code")
    if new_code and new_code != vehicle.vehicle_code:
        existing = vehicle_repository.get_vehicle_by_code(db, new_code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Vehicle code already exists",
            )

    new_registration = update_data.get("registration_number")
    if (
        new_registration
        and new_registration != vehicle.registration_number
    ):
        existing = vehicle_repository.get_vehicle_by_registration(
            db, new_registration
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Vehicle registration number already exists",
            )

    if "location_id" in update_data:
        validate_location(db, update_data["location_id"])

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field is required for update",
        )

    return vehicle_repository.update_vehicle(
        db,
        vehicle,
        update_data,
    )


def update_vehicle_status(
    db: Session,
    vehicle_id: UUID,
    new_status: VehicleStatus,
) -> Vehicle:
    vehicle = get_vehicle(db, vehicle_id)

    if vehicle.status == VehicleStatus.RETIRED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Retired vehicles cannot change status",
        )

    vehicle.is_active = new_status != VehicleStatus.RETIRED

    return vehicle_repository.update_vehicle_status(
        db,
        vehicle,
        new_status,
    )