from typing import Any

from pydantic import BaseModel, Field


class ReportPagination(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class AdvancedReportResponse(BaseModel):
    items: list[dict[str, Any]] = Field(
        default_factory=list
    )
    pagination: ReportPagination


class CollectionReportItem(BaseModel):
    report_date: str | None = None
    total_requests: int = 0
    completed_collections: int = 0
    pending_collections: int = 0
    missed_collections: int = 0
    total_collected_kg: float = 0.0


class ZonePerformanceItem(BaseModel):
    zone_id: str | None = None
    zone_name: str | None = None
    total_pickups: int = 0
    completed_pickups: int = 0
    pending_pickups: int = 0
    missed_pickups: int = 0
    total_collected_kg: float = 0.0
    collection_efficiency_percentage: float = 0.0


class DriverPerformanceItem(BaseModel):
    driver_id: str | None = None
    driver_name: str | None = None
    total_assignments: int = 0
    completed_assignments: int = 0
    total_collected_kg: float = 0.0
    completion_percentage: float = 0.0


class VehicleUtilizationItem(BaseModel):
    vehicle_id: str | None = None
    vehicle_code: str | None = None
    registration_number: str | None = None
    total_assignments: int = 0
    completed_assignments: int = 0
    total_collected_kg: float = 0.0
    utilization_percentage: float = 0.0


class WasteCategoryReportItem(BaseModel):
    category_id: str | None = None
    category_name: str | None = None
    total_quantity_kg: float = 0.0
    recyclable_quantity_kg: float = 0.0
    non_recyclable_quantity_kg: float = 0.0
    contaminated_quantity_kg: float = 0.0


class RecyclingCenterReportItem(BaseModel):
    recycling_center_id: str | None = None
    recycling_center_name: str | None = None
    total_received_kg: float = 0.0
    total_processed_kg: float = 0.0
    total_recycled_kg: float = 0.0
    total_disposed_kg: float = 0.0


class RecyclingYieldReportItem(BaseModel):
    recycling_center_id: str | None = None
    recycling_center_name: str | None = None
    input_quantity_kg: float = 0.0
    output_quantity_kg: float = 0.0
    residual_quantity_kg: float = 0.0
    recycling_yield_percentage: float = 0.0


class DisposalReportItem(BaseModel):
    disposal_id: str | None = None
    disposal_number: str | None = None
    recycling_center_name: str | None = None
    waste_category_name: str | None = None
    disposal_method: str | None = None
    disposal_quantity_kg: float = 0.0
    status: str | None = None


class EnvironmentalImpactReportItem(BaseModel):
    period_start_date: str | None = None
    period_end_date: str | None = None
    total_waste_collected_kg: float = 0.0
    total_recyclable_waste_kg: float = 0.0
    total_waste_recycled_kg: float = 0.0
    total_waste_disposed_kg: float = 0.0
    recycling_rate_percentage: float = 0.0