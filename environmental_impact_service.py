
from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import CollectionTrackingStatus
from models.environmental_impact import EnvironmentalImpactSnapshot
from repositories.environmental_impact_repository import (
    EnvironmentalImpactRepository,
)
from schemas.environmental_impact import (
    EnvironmentalImpactSummary,
    WasteCategoryDistribution,
    MonthlyRecyclingTrend,
)


class EnvironmentalImpactService:

    @staticmethod
    def _quantity(value):
        return float(value or 0)

    @staticmethod
    def _validate_dates(start_date, end_date):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date cannot be after end date",
            )

    @staticmethod
    def get_data(db, start_date=None, end_date=None):
        EnvironmentalImpactService._validate_dates(
            start_date,
            end_date,
        )

        return {
            "trackings": EnvironmentalImpactRepository.get_collection_trackings(
                db, start_date, end_date
            ),
            "segregations": EnvironmentalImpactRepository.get_segregations(
                db, start_date, end_date
            ),
            "processings": EnvironmentalImpactRepository.get_processings(
                db, start_date, end_date
            ),
            "disposals": EnvironmentalImpactRepository.get_disposals(
                db, start_date, end_date
            ),
        }

    @staticmethod
    def get_summary(db, start_date=None, end_date=None):
        data = EnvironmentalImpactService.get_data(
            db, start_date, end_date
        )

        total_collected = sum(
            EnvironmentalImpactService._quantity(
                item.collected_quantity_kg
            )
            for item in data["trackings"]
        )

        total_recyclable = sum(
            EnvironmentalImpactService._quantity(
                item.recyclable_quantity_kg
            )
            for item in data["segregations"]
        )

        total_recycled = sum(
            EnvironmentalImpactService._quantity(
                item.output_quantity_kg
            )
            for item in data["processings"]
        )

        total_disposed = sum(
            EnvironmentalImpactService._quantity(
                item.disposal_quantity_kg
            )
            for item in data["disposals"]
        )

        recycling_rate = (
            total_recycled / total_collected * 100
            if total_collected > 0
            else 0
        )

        return EnvironmentalImpactSummary(
            start_date=start_date,
            end_date=end_date,
            total_waste_collected_kg=round(total_collected, 2),
            total_recyclable_waste_kg=round(total_recyclable, 2),
            total_waste_recycled_kg=round(total_recycled, 2),
            total_waste_disposed_kg=round(total_disposed, 2),
            recycling_rate_percentage=round(recycling_rate, 2),
        )

    @staticmethod
    def get_category_distribution(db, start_date=None, end_date=None):
        data = EnvironmentalImpactService.get_data(
            db, start_date, end_date
        )

        categories = EnvironmentalImpactRepository.get_categories(db)

        quantities = defaultdict(float)

        for item in data["segregations"]:
            quantities[item.waste_category_id] += (
                EnvironmentalImpactService._quantity(
                    item.incoming_quantity_kg
                )
            )

        return [
            WasteCategoryDistribution(
                category_id=category.id,
                category_name=category.name,
                total_quantity_kg=round(
                    quantities[category.id], 2
                ),
                is_recyclable=category.is_recyclable,
            )
            for category in categories
        ]

    @staticmethod
    def get_monthly_trends(db, start_date=None, end_date=None):
        data = EnvironmentalImpactService.get_data(
            db, start_date, end_date
        )

        monthly = defaultdict(float)

        for item in data["processings"]:
            if item.processed_at:
                key = (
                    item.processed_at.year,
                    item.processed_at.month,
                )
                monthly[key] += EnvironmentalImpactService._quantity(
                    item.output_quantity_kg
                )

        return [
            MonthlyRecyclingTrend(
                year=year,
                month=month,
                total_recycled_kg=round(quantity, 2),
            )
            for (year, month), quantity in sorted(monthly.items())
        ]

    @staticmethod
    def generate_snapshot(
        db,
        current_user_id,
        start_date=None,
        end_date=None,
    ):
        summary = EnvironmentalImpactService.get_summary(
            db, start_date, end_date
        )

        categories = EnvironmentalImpactService.get_category_distribution(
            db, start_date, end_date
        )

        trends = EnvironmentalImpactService.get_monthly_trends(
            db, start_date, end_date
        )

        category_data = [
            item.model_dump(mode="json")
            for item in categories
        ]

        trend_data = [
            item.model_dump(mode="json")
            for item in trends
        ]

        summary_data = summary.model_dump(mode="json")

        snapshot = EnvironmentalImpactSnapshot(
            id=uuid4(),
            period_start_date=start_date,
            period_end_date=end_date,
            total_waste_collected_kg=Decimal(
                str(summary.total_waste_collected_kg)
            ),
            total_recyclable_waste_kg=Decimal(
                str(summary.total_recyclable_waste_kg)
            ),
            total_waste_recycled_kg=Decimal(
                str(summary.total_waste_recycled_kg)
            ),
            total_waste_disposed_kg=Decimal(
                str(summary.total_waste_disposed_kg)
            ),
            recycling_rate_percentage=Decimal(
                str(summary.recycling_rate_percentage)
            ),
            waste_category_distribution=category_data,
            monthly_recycling_trends=trend_data,
            environmental_summary=summary_data,
            generated_by_user_id=current_user_id,
        )

        return EnvironmentalImpactRepository.create_snapshot(
            db, snapshot
        )

    @staticmethod
    def get_snapshots(db):
        return EnvironmentalImpactRepository.get_snapshots(db)

    @staticmethod
    def get_snapshot(db, snapshot_id):
        snapshot = EnvironmentalImpactRepository.get_snapshot_by_id(
            db, snapshot_id
        )

        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Environmental impact snapshot not found",
            )

        return snapshot
