from uuid import UUID

from sqlalchemy.orm import Session

from models.vehicle import Vehicle
from core.constants import VehicleStatus, VehicleType


def create_vehicle(db: Session, vehicle_data: dict) -> Vehicle:
    vehicle = Vehicle(**vehicle_data)
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def get_vehicle_by_id(db: Session, vehicle_id: UUID) -> Vehicle | None:
    return db.query(Vehicle).filter(
        Vehicle.id == vehicle_id
    ).first()


def get_vehicle_by_code(db: Session, vehicle_code: str) -> Vehicle | None:
    return db.query(Vehicle).filter(
        Vehicle.vehicle_code == vehicle_code
    ).first()


def get_vehicle_by_registration(
    db: Session,
    registration_number: str,
) -> Vehicle | None:
    return db.query(Vehicle).filter(
        Vehicle.registration_number == registration_number
    ).first()


def list_vehicles(
    db: Session,
    status: VehicleStatus | None = None,
    vehicle_type: VehicleType | None = None,
    location_id: UUID | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Vehicle]:
    query = db.query(Vehicle)

    if status is not None:
        query = query.filter(Vehicle.status == status)

    if vehicle_type is not None:
        query = query.filter(Vehicle.vehicle_type == vehicle_type)

    if location_id is not None:
        query = query.filter(Vehicle.location_id == location_id)

    return (
        query.order_by(Vehicle.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_vehicle(
    db: Session,
    vehicle: Vehicle,
    update_data: dict,
) -> Vehicle:
    for field, value in update_data.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle


def update_vehicle_status(
    db: Session,
    vehicle: Vehicle,
    status: VehicleStatus,
) -> Vehicle:
    vehicle.status = status
    db.commit()
    db.refresh(vehicle)
    return vehicle