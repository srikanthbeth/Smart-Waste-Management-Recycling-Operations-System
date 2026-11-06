from uuid import UUID

from sqlalchemy.orm import Session

from models.vehicle_maintenance import VehicleMaintenance
from core.constants import MaintenanceType, MaintenanceStatus, MaintenancePriority


class VehicleMaintenanceRepository:

    @staticmethod
    def create(db: Session, maintenance: VehicleMaintenance):
        db.add(maintenance)
        db.commit()
        db.refresh(maintenance)
        return maintenance

    @staticmethod
    def get_by_id(db: Session, maintenance_id: UUID):
        return (
            db.query(VehicleMaintenance)
            .filter(VehicleMaintenance.id == maintenance_id)
            .first()
        )

    @staticmethod
    def get_by_number(db: Session, maintenance_number: str):
        return (
            db.query(VehicleMaintenance)
            .filter(VehicleMaintenance.maintenance_number == maintenance_number)
            .first()
        )

    @staticmethod
    def list_all(
        db: Session,
        vehicle_id: UUID | None = None,
        maintenance_type: MaintenanceType | None = None,
        status: MaintenanceStatus | None = None,
        priority: MaintenancePriority | None = None,
    ):
        query = db.query(VehicleMaintenance)

        if vehicle_id:
            query = query.filter(VehicleMaintenance.vehicle_id == vehicle_id)

        if maintenance_type:
            query = query.filter(
                VehicleMaintenance.maintenance_type == maintenance_type
            )

        if status:
            query = query.filter(VehicleMaintenance.status == status)

        if priority:
            query = query.filter(VehicleMaintenance.priority == priority)

        return query.order_by(VehicleMaintenance.created_at.desc()).all()

    @staticmethod
    def get_vehicle_history(db: Session, vehicle_id: UUID):
        return (
            db.query(VehicleMaintenance)
            .filter(VehicleMaintenance.vehicle_id == vehicle_id)
            .order_by(VehicleMaintenance.created_at.desc())
            .all()
        )

    @staticmethod
    def update(db: Session, maintenance: VehicleMaintenance):
        db.add(maintenance)
        db.commit()
        db.refresh(maintenance)
        return maintenance