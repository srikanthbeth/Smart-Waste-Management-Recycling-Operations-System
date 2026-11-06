from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CollectionPerformanceSummary(BaseModel):
    start_date: date | None
    end_date: date | None

    total_pickup_requests: int
    completed_pickups: int
    missed_pickups: int

    average_collection_time_minutes: float
    collection_efficiency_percentage: float

    active_vehicles: int
    utilized_vehicles: int
    vehicle_utilization_percentage: float


class ZoneCollectionPerformance(BaseModel):
    zone_id: UUID | None
    zone_name: str

    total_pickups: int
    completed_pickups: int
    missed_pickups: int

    collection_efficiency_percentage: float


class DriverCollectionPerformance(BaseModel):
    driver_id: UUID
    driver_code: str

    total_assignments: int
    completed_pickups: int
    missed_pickups: int

    average_collection_time_minutes: float


class VehicleCollectionPerformance(BaseModel):
    vehicle_id: UUID
    vehicle_code: str
    registration_number: str

    total_assignments: int
    completed_pickups: int
    missed_pickups: int

    is_utilized: bool

    model_config = ConfigDict(from_attributes=True)