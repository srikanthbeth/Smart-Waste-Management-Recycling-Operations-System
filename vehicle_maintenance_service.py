from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.vehicle import Vehicle
from models.user import User
from models.vehicle_maintenance import VehicleMaintenance

from core.constants import MaintenanceType, MaintenanceStatus

from schemas.vehicle_maintenance import (
    VehicleMaintenanceCreate,
    VehicleMaintenanceUpdate,
)

from repositories.vehicle_maintenance_repository import (
    VehicleMaintenanceRepository,
)


class VehicleMaintenanceService:

    @staticmethod
    def create_maintenance(
        db: Session,
        payload: VehicleMaintenanceCreate,
        current_user: User,
    ):
        vehicle = db.query(Vehicle).filter(
            Vehicle.id == payload.vehicle_id
        ).first()

        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found",
            )

        if payload.technician_id:
            technician = db.query(User).filter(
                User.id == payload.technician_id
            ).first()

            if not technician:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Technician not found",
                )

        if (
            payload.maintenance_type == MaintenanceType.PREVENTIVE
            and not payload.scheduled_date
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Scheduled date is required for preventive maintenance",
            )

        if (
            payload.maintenance_type == MaintenanceType.BREAKDOWN
            and not payload.breakdown_report
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Breakdown report is required",
            )

        initial_status = (
            MaintenanceStatus.SCHEDULED
            if payload.scheduled_date
            else MaintenanceStatus.REQUESTED
        )

        downtime_start = None

        if payload.maintenance_type in (
            MaintenanceType.BREAKDOWN,
            MaintenanceType.EMERGENCY,
        ):
            downtime_start = datetime.now(timezone.utc)

        maintenance = VehicleMaintenance(
            maintenance_number=f"VM-{uuid4().hex[:10].upper()}",
            vehicle_id=payload.vehicle_id,
            maintenance_type=payload.maintenance_type,
            priority=payload.priority,
            status=initial_status,
            title=payload.title.strip(),
            description=payload.description.strip(),
            scheduled_date=payload.scheduled_date,
            next_maintenance_date=payload.next_maintenance_date,
            breakdown_report=payload.breakdown_report,
            service_provider=payload.service_provider,
            technician_id=payload.technician_id,
            maintenance_cost=payload.maintenance_cost,
            downtime_start=downtime_start,
            requested_by_user_id=current_user.id,
        )

        return VehicleMaintenanceRepository.create(db, maintenance)

    @staticmethod
    def update_maintenance(
        db: Session,
        maintenance_id: UUID,
        payload: VehicleMaintenanceUpdate,
    ):
        maintenance = VehicleMaintenanceRepository.get_by_id(
            db, maintenance_id
        )

        if not maintenance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Maintenance record not found",
            )

        update_data = payload.model_dump(exclude_unset=True)

        technician_id = update_data.get("technician_id")

        if technician_id:
            technician = db.query(User).filter(
                User.id == technician_id
            ).first()

            if not technician:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Technician not found",
                )

        new_status = update_data.get("status")

        if (
            new_status == MaintenanceStatus.IN_PROGRESS
            and not maintenance.downtime_start
        ):
            maintenance.downtime_start = datetime.now(timezone.utc)

        for field, value in update_data.items():
            setattr(maintenance, field, value)

        if maintenance.status == MaintenanceStatus.COMPLETED:
            now = datetime.now(timezone.utc)

            maintenance.completed_at = now

            if maintenance.downtime_start:
                maintenance.downtime_end = now

                duration = (
                    maintenance.downtime_end - maintenance.downtime_start
                ).total_seconds() / 3600

                maintenance.downtime_hours = Decimal(
                    str(round(duration, 2))
                )

        if maintenance.downtime_start and maintenance.downtime_end:
            if maintenance.downtime_end < maintenance.downtime_start:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Downtime end cannot be earlier than downtime start",
                )

            duration = (
                maintenance.downtime_end - maintenance.downtime_start
            ).total_seconds() / 3600

            maintenance.downtime_hours = Decimal(
                str(round(duration, 2))
            )

        return VehicleMaintenanceRepository.update(db, maintenance)

    @staticmethod
    def get_maintenance(db: Session, maintenance_id: UUID):
        maintenance = VehicleMaintenanceRepository.get_by_id(
            db, maintenance_id
        )

        if not maintenance:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Maintenance record not found",
            )

        return maintenance

    @staticmethod
    def list_maintenance(
        db: Session,
        vehicle_id: UUID | None = None,
        maintenance_type: MaintenanceType | None = None,
        status: MaintenanceStatus | None = None,
        priority=None,
    ):
        return VehicleMaintenanceRepository.list_all(
            db,
            vehicle_id=vehicle_id,
            maintenance_type=maintenance_type,
            status=status,
            priority=priority,
        )

    @staticmethod
    def get_vehicle_history(db: Session, vehicle_id: UUID):
        vehicle = db.query(Vehicle).filter(
            Vehicle.id == vehicle_id
        ).first()

        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found",
            )

        return VehicleMaintenanceRepository.get_vehicle_history(
            db, vehicle_id
        )