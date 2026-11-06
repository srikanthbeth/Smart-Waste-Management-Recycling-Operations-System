from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class CollectionDashboard(BaseModel):
    total_collection_requests: int = 0
    completed_collections: int = 0
    pending_pickups: int = 0
    missed_collections: int = 0


class VehicleDashboard(BaseModel):
    total_vehicles: int = 0
    available_vehicles: int = 0
    assigned_vehicles: int = 0
    maintenance_vehicles: int = 0
    out_of_service_vehicles: int = 0
    retired_vehicles: int = 0


class RecyclingDashboard(BaseModel):
    active_recycling_centers: int = 0

    total_waste_collected_kg: float = 0.0
    total_waste_recycled_kg: float = 0.0

    recycling_efficiency_percentage: float = Field(
        default=0.0,
        ge=0,
        le=100,
    )


class ComplaintDashboard(BaseModel):
    pending_complaints: int = 0
    total_complaints: int = 0


class MaintenanceDashboard(BaseModel):
    total_maintenance_records: int = 0
    pending_maintenance: int = 0
    in_progress_maintenance: int = 0
    completed_maintenance: int = 0
    overdue_maintenance: int = 0


class AdminDashboardResponse(BaseModel):
    total_customers: int = 0

    collections: CollectionDashboard

    vehicles: VehicleDashboard

    recycling: RecyclingDashboard

    complaints: ComplaintDashboard

    maintenance: MaintenanceDashboard

    generated_at: date | None = None


class DashboardSummaryResponse(BaseModel):
    total_customers: int = 0
    total_collection_requests: int = 0
    completed_collections: int = 0
    pending_pickups: int = 0
    missed_collections: int = 0
    total_vehicles: int = 0
    available_vehicles: int = 0
    active_recycling_centers: int = 0
    total_waste_collected_kg: float = 0.0
    total_waste_recycled_kg: float = 0.0
    recycling_efficiency_percentage: float = 0.0
    pending_complaints: int = 0
    maintenance_status: dict[str, Any] = Field(
        default_factory=dict
    )