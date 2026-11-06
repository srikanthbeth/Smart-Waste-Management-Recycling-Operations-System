from sqlalchemy.orm import Session
from sqlalchemy import func

from models.customer import Customer
from models.pickup import Pickup
from models.vehicle import Vehicle
from models.recycling_center import RecyclingCenter
from models.collection_tracking import CollectionTracking
from models.waste_processing import WasteProcessing
from models.customer_complaint import CustomerComplaint
from models.vehicle_maintenance import VehicleMaintenance

from core.constants import (
    PickupStatus,
    VehicleStatus,
    CollectionTrackingStatus,
    RecyclingCenterStatus,
)


def get_total_customers(db: Session) -> int:
    return db.query(Customer).count()


def get_collection_statistics(db: Session) -> dict:
    total = db.query(Pickup).count()

    completed = db.query(Pickup).filter(
        Pickup.status == PickupStatus.COMPLETED
    ).count()

    pending = db.query(Pickup).filter(
        Pickup.status.in_([
            PickupStatus.REQUESTED,
            PickupStatus.APPROVED,
            PickupStatus.SCHEDULED,
            PickupStatus.ASSIGNED,
        ])
    ).count()

    missed = db.query(CollectionTracking).filter(
        CollectionTracking.status == CollectionTrackingStatus.FAILED
    ).count()

    return {
        "total_collection_requests": total,
        "completed_collections": completed,
        "pending_pickups": pending,
        "missed_collections": missed,
    }


def get_vehicle_statistics(db: Session) -> dict:
    return {
        "total_vehicles": db.query(Vehicle).count(),

        "available_vehicles": db.query(Vehicle).filter(
            Vehicle.status == VehicleStatus.AVAILABLE
        ).count(),

        "assigned_vehicles": db.query(Vehicle).filter(
            Vehicle.status == VehicleStatus.ASSIGNED
        ).count(),

        "maintenance_vehicles": db.query(Vehicle).filter(
            Vehicle.status == VehicleStatus.MAINTENANCE
        ).count(),

        "out_of_service_vehicles": db.query(Vehicle).filter(
            Vehicle.status == VehicleStatus.OUT_OF_SERVICE
        ).count(),

        "retired_vehicles": db.query(Vehicle).filter(
            Vehicle.status == VehicleStatus.RETIRED
        ).count(),
    }


def get_recycling_statistics(db: Session) -> dict:
    active_centers = db.query(RecyclingCenter).filter(
        RecyclingCenter.status == RecyclingCenterStatus.ACTIVE
    ).count()

    collected = db.query(
        func.coalesce(
            func.sum(CollectionTracking.collected_quantity_kg), 0
        )
    ).filter(
        CollectionTracking.status.in_([
            CollectionTrackingStatus.COMPLETED,
            CollectionTrackingStatus.PARTIALLY_COMPLETED,
        ])
    ).scalar()

    recycled = db.query(
        func.coalesce(
            func.sum(WasteProcessing.output_quantity_kg), 0
        )
    ).scalar()

    collected = float(collected or 0)
    recycled = float(recycled or 0)

    efficiency = (
        (recycled / collected) * 100
        if collected > 0
        else 0.0
    )

    return {
        "active_recycling_centers": active_centers,
        "total_waste_collected_kg": round(collected, 2),
        "total_waste_recycled_kg": round(recycled, 2),
        "recycling_efficiency_percentage": round(
            efficiency, 2
        ),
    }


def get_complaint_statistics(db: Session) -> dict:
    total = db.query(CustomerComplaint).count()

    pending = db.query(CustomerComplaint).filter(
        CustomerComplaint.status.in_(["open", "in_progress"])
    ).count()

    return {
        "total_complaints": total,
        "pending_complaints": pending,
    }


def get_maintenance_statistics(db: Session) -> dict:
    total = db.query(VehicleMaintenance).count()

    pending = db.query(VehicleMaintenance).filter(
        VehicleMaintenance.status == "scheduled"
    ).count()

    in_progress = db.query(VehicleMaintenance).filter(
        VehicleMaintenance.status == "in_progress"
    ).count()

    completed = db.query(VehicleMaintenance).filter(
        VehicleMaintenance.status == "completed"
    ).count()

    return {
        "total_maintenance_records": total,
        "pending_maintenance": pending,
        "in_progress_maintenance": in_progress,
        "completed_maintenance": completed,
    }