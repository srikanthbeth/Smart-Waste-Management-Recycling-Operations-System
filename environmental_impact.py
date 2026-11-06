
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EnvironmentalImpactSummary(BaseModel):
    start_date: date | None
    end_date: date | None

    total_waste_collected_kg: float
    total_recyclable_waste_kg: float
    total_waste_recycled_kg: float
    total_waste_disposed_kg: float

    recycling_rate_percentage: float


class WasteCategoryDistribution(BaseModel):
    category_id: UUID
    category_name: str
    total_quantity_kg: float
    is_recyclable: bool


class MonthlyRecyclingTrend(BaseModel):
    year: int
    month: int
    total_recycled_kg: float


class EnvironmentalImpactSnapshotResponse(BaseModel):
    id: UUID
    period_start_date: date | None
    period_end_date: date | None

    total_waste_collected_kg: float
    total_recyclable_waste_kg: float
    total_waste_recycled_kg: float
    total_waste_disposed_kg: float

    recycling_rate_percentage: float

    waste_category_distribution: list[WasteCategoryDistribution]
    monthly_recycling_trends: list
    environmental_summary: dict

    generated_by_user_id: UUID | None
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)
