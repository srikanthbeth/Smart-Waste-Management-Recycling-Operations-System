from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import (
    MaintenanceType,
    MaintenanceStatus,
    MaintenancePriority,
)


class VehicleMaintenanceCreate(BaseModel):
    vehicle_id: UUID
    maintenance_type: MaintenanceType
    priority: MaintenancePriority = MaintenancePriority.MEDIUM

    title: str = Field(min_length=3, max_length=150)
    description: str = Field(min_length=5)

    scheduled_date: date | None = None
    next_maintenance_date: date | None = None

    breakdown_report: str | None = None
    service_provider: str | None = Field(default=None, max_length=150)

    technician_id: UUID | None = None
    maintenance_cost: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)

    resolution_remarks: str | None = None


class VehicleMaintenanceUpdate(BaseModel):
    priority: MaintenancePriority | None = None
    status: MaintenanceStatus | None = None

    scheduled_date: date | None = None
    next_maintenance_date: date | None = None

    technician_id: UUID | None = None
    service_provider: str | None = Field(default=None, max_length=150)

    maintenance_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    downtime_start: datetime | None = None
    downtime_end: datetime | None = None

    resolution_remarks: str | None = None


class VehicleMaintenanceResponse(BaseModel):
    id: UUID
    maintenance_number: str
    vehicle_id: UUID

    maintenance_type: MaintenanceType
    priority: MaintenancePriority
    status: MaintenanceStatus

    title: str
    description: str

    scheduled_date: date | None
    next_maintenance_date: date | None

    breakdown_report: str | None
    service_provider: str | None
    technician_id: UUID | None

    maintenance_cost: Decimal

    downtime_start: datetime | None
    downtime_end: datetime | None
    downtime_hours: Decimal | None

    completed_at: datetime | None
    resolution_remarks: str | None

    requested_by_user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)