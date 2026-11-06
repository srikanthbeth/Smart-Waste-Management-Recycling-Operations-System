
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from repositories.advanced_reports_repository import (
    AdvancedReportsRepository,
)


class AdvancedReportsService:
    def __init__(self, db: Session):
        self.repository = AdvancedReportsRepository(db)

    @staticmethod
    def validate_filters(
        start_date=None,
        end_date=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Start date cannot be after end date.",
            )

        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page must be greater than or equal to 1.",
            )

        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page size must be between 1 and 100.",
            )

        if sort_order.lower() not in ("asc", "desc"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Sort order must be asc or desc.",
            )

    @staticmethod
    def serialize(value):
        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, (UUID, date)):
            return str(value)

        if hasattr(value, "value"):
            return value.value

        return value

    @classmethod
    def serialize_result(cls, result):
        items = []

        for row in result["items"]:
            if isinstance(row, dict):
                item = row.copy()
            elif hasattr(row, "_mapping"):
                item = dict(row._mapping)
            else:
                item = dict(row)

            item = {
                key: cls.serialize(value)
                for key, value in item.items()
            }

            items.append(item)

        return {
            "items": items,
            "pagination": result["pagination"],
        }

    @staticmethod
    def calculate_percentage(numerator, denominator):
        if not denominator:
            return 0.0

        return round((float(numerator) / float(denominator)) * 100, 2)

    def _prepare_result(self, result, percentage_fields=None):
        response = self.serialize_result(result)

        if percentage_fields:
            for item in response["items"]:
                for output_field, numerator_field, denominator_field in percentage_fields:
                    item[output_field] = self.calculate_percentage(
                        item.get(numerator_field, 0),
                        item.get(denominator_field, 0),
                    )

        return response

    def get_daily_collection_reports(
        self,
        start_date=None,
        end_date=None,
        zone_id=None,
        waste_category_id=None,
        status=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        self.validate_filters(
            start_date,
            end_date,
            page,
            page_size,
            sort_order,
        )

        result = self.repository.get_daily_collection_reports(
            start_date=start_date,
            end_date=end_date,
            zone_id=zone_id,
            waste_category_id=waste_category_id,
            status=status,
            page=page,
            page_size=page_size,
            sort_order=sort_order,
        )

        return self._prepare_result(result)

    def get_monthly_collection_reports(
        self,
        start_date=None,
        end_date=None,
        zone_id=None,
        waste_category_id=None,
        status=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        self.validate_filters(
            start_date,
            end_date,
            page,
            page_size,
            sort_order,
        )

        result = self.repository.get_monthly_collection_reports(
            start_date=start_date,
            end_date=end_date,
            zone_id=zone_id,
            waste_category_id=waste_category_id,
            status=status,
            page=page,
            page_size=page_size,
            sort_order=sort_order,
        )

        return self._prepare_result(result)

    def get_zone_performance(self, **filters):
        self.validate_filters(
            filters.get("start_date"),
            filters.get("end_date"),
            filters.get("page", 1),
            filters.get("page_size", 20),
            filters.get("sort_order", "desc"),
        )

        result = self.repository.get_zone_performance(**filters)

        return self._prepare_result(
            result,
            percentage_fields=[
                (
                    "collection_efficiency_percentage",
                    "completed_pickups",
                    "total_pickups",
                )
            ],
        )

    def get_driver_performance(self, **filters):
        self.validate_filters(
            filters.get("start_date"),
            filters.get("end_date"),
            filters.get("page", 1),
            filters.get("page_size", 20),
            filters.get("sort_order", "desc"),
        )

        result = self.repository.get_driver_performance(**filters)

        return self._prepare_result(
            result,
            percentage_fields=[
                (
                    "completion_percentage",
                    "completed_assignments",
                    "total_assignments",
                )
            ],
        )

    def get_vehicle_utilization(self, **filters):
        self.validate_filters(
            filters.get("start_date"),
            filters.get("end_date"),
            filters.get("page", 1),
            filters.get("page_size", 20),
            filters.get("sort_order", "desc"),
        )

        result = self.repository.get_vehicle_utilization(**filters)

        return self._prepare_result(
            result,
            percentage_fields=[
                (
                    "utilization_percentage",
                    "completed_assignments",
                    "total_assignments",
                )
            ],
        )

    def get_waste_category_reports(self, **filters):
        self.validate_filters(
            filters.get("start_date"),
            filters.get("end_date"),
            filters.get("page", 1),
            filters.get("page_size", 20),
            filters.get("sort_order", "desc"),
        )

        result = self.repository.get_waste_category_reports(**filters)

        return self._prepare_result(result)

    def get_recycling_center_performance(self, **filters):
        self.validate_filters(
            filters.get("start_date"),
            filters.get("end_date"),
            filters.get("page", 1),
            filters.get("page_size", 20),
            filters.get("sort_order", "desc"),
        )

        result = self.repository.get_recycling_center_performance(
            **filters
        )

        return self._prepare_result(result)

    def get_recycling_yield_reports(self, **filters):
        self.validate_filters(
            filters.get("start_date"),
            filters.get("end_date"),
            filters.get("page", 1),
            filters.get("page_size", 20),
            filters.get("sort_order", "desc"),
        )

        result = self.repository.get_recycling_yield_reports(**filters)
        response = self.serialize_result(result)

        for item in response["items"]:
            item["recycling_yield_percentage"] = (
                self.calculate_percentage(
                    item.get("output_quantity_kg", 0),
                    item.get("input_quantity_kg", 0),
                )
            )

        return response

    def get_disposal_reports(self, **filters):
        self.validate_filters(
            filters.get("start_date"),
            filters.get("end_date"),
            filters.get("page", 1),
            filters.get("page_size", 20),
            filters.get("sort_order", "desc"),
        )

        result = self.repository.get_disposal_reports(**filters)

        return self._prepare_result(result)

    def get_environmental_impact_reports(self, **filters):
        self.validate_filters(
            filters.get("start_date"),
            filters.get("end_date"),
            filters.get("page", 1),
            filters.get("page_size", 20),
            filters.get("sort_order", "desc"),
        )

        result = self.repository.get_environmental_impact_reports(
            **filters
        )

        return self._prepare_result(result)
