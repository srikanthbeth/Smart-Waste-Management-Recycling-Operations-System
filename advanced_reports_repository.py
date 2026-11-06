
from math import ceil

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from core.constants import (
    AssignmentStatus,
    CollectionTrackingStatus,
    PickupStatus,
    WasteTransferStatus,
)
from models.collection_assignment import CollectionAssignment
from models.collection_tracking import CollectionTracking
from models.driver import Driver
from models.environmental_impact import EnvironmentalImpactSnapshot
from models.location import Location
from models.pickup import Pickup
from models.recycling_center import RecyclingCenter
from models.user import User
from models.vehicle import Vehicle
from models.waste_category import WasteCategory
from models.waste_disposal import WasteDisposal
from models.waste_processing import WasteProcessing
from models.waste_segregation import WasteSegregation
from models.waste_transfer import WasteTransfer


class AdvancedReportsRepository:

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _paginate(query, page: int, page_size: int):
        page = max(page, 1)
        page_size = max(1, min(page_size, 100))

        total = query.order_by(None).count()
        total_pages = ceil(total / page_size) if total else 0

        rows = (
            query
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": rows,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
            },
        }

    @staticmethod
    def _apply_date_filter(
        query,
        column,
        start_date=None,
        end_date=None,
    ):
        if start_date:
            query = query.filter(column >= start_date)

        if end_date:
            query = query.filter(column <= end_date)

        return query

    @staticmethod
    def _apply_pickup_filters(
        query,
        start_date=None,
        end_date=None,
        zone_id=None,
        waste_category_id=None,
        status=None,
    ):
        query = AdvancedReportsRepository._apply_date_filter(
            query,
            Pickup.preferred_date,
            start_date,
            end_date,
        )

        if zone_id:
            query = query.filter(Pickup.location_id == zone_id)

        if waste_category_id:
            query = query.filter(
                Pickup.waste_category_id == waste_category_id
            )

        if status:
            query = query.filter(Pickup.status == status)

        return query

    # =========================================================
    # DAILY AND MONTHLY COLLECTION REPORTS
    # =========================================================

    def get_collection_reports(
        self,
        group_by="day",
        start_date=None,
        end_date=None,
        zone_id=None,
        waste_category_id=None,
        status=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        if group_by == "month":
            report_date = func.to_char(
                Pickup.preferred_date,
                "YYYY-MM",
            )
        else:
            report_date = func.to_char(
                Pickup.preferred_date,
                "YYYY-MM-DD",
            )

        # Keep ordering identical to the grouped expression.
        ordering = report_date

        query = (
            self.db.query(
                report_date.label("report_date"),
                func.count(
                    func.distinct(Pickup.id)
                ).label("total_requests"),
                func.count(
                    func.distinct(
                        case(
                            (
                                CollectionTracking.status
                                == CollectionTrackingStatus.COMPLETED,
                                Pickup.id,
                            )
                        )
                    )
                ).label("completed_collections"),
                func.count(
                    func.distinct(
                        case(
                            (
                                CollectionTracking.status
                                == CollectionTrackingStatus.FAILED,
                                Pickup.id,
                            )
                        )
                    )
                ).label("missed_collections"),
                func.count(
                    func.distinct(
                        case(
                            (
                                Pickup.status.notin_([
                                    PickupStatus.COMPLETED,
                                    PickupStatus.CANCELLED,
                                    PickupStatus.REJECTED,
                                ]),
                                Pickup.id,
                            )
                        )
                    )
                ).label("pending_collections"),
                func.coalesce(
                    func.sum(
                        CollectionTracking.collected_quantity_kg
                    ),
                    0,
                ).label("total_collected_kg"),
            )
            .outerjoin(
                CollectionTracking,
                CollectionTracking.pickup_id == Pickup.id,
            )
        )

        query = self._apply_pickup_filters(
            query,
            start_date,
            end_date,
            zone_id,
            waste_category_id,
            status,
        )

        query = query.group_by(report_date)

        if sort_order.lower() == "asc":
            query = query.order_by(ordering.asc())
        else:
            query = query.order_by(ordering.desc())

        return self._paginate(query, page, page_size)

    def get_daily_collection_reports(self, **filters):
        return self.get_collection_reports(
            group_by="day",
            **filters,
        )

    def get_monthly_collection_reports(self, **filters):
        return self.get_collection_reports(
            group_by="month",
            **filters,
        )

    # =========================================================
    # ZONE-WISE PERFORMANCE
    # =========================================================

    def get_zone_performance(
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
        query = (
            self.db.query(
                Location.id.label("zone_id"),
                Location.name.label("zone_name"),
                func.count(
                    func.distinct(Pickup.id)
                ).label("total_pickups"),
                func.count(
                    func.distinct(
                        case(
                            (
                                CollectionTracking.status
                                == CollectionTrackingStatus.COMPLETED,
                                Pickup.id,
                            )
                        )
                    )
                ).label("completed_pickups"),
                func.count(
                    func.distinct(
                        case(
                            (
                                Pickup.status.notin_([
                                    PickupStatus.COMPLETED,
                                    PickupStatus.CANCELLED,
                                    PickupStatus.REJECTED,
                                ]),
                                Pickup.id,
                            )
                        )
                    )
                ).label("pending_pickups"),
                func.count(
                    func.distinct(
                        case(
                            (
                                CollectionTracking.status
                                == CollectionTrackingStatus.FAILED,
                                Pickup.id,
                            )
                        )
                    )
                ).label("missed_pickups"),
                func.coalesce(
                    func.sum(
                        CollectionTracking.collected_quantity_kg
                    ),
                    0,
                ).label("total_collected_kg"),
            )
            .join(
                Location,
                Location.id == Pickup.location_id,
            )
            .outerjoin(
                CollectionTracking,
                CollectionTracking.pickup_id == Pickup.id,
            )
        )

        query = self._apply_pickup_filters(
            query,
            start_date,
            end_date,
            zone_id,
            waste_category_id,
            status,
        )

        query = query.group_by(Location.id, Location.name)

        if sort_order.lower() == "asc":
            query = query.order_by(Location.name.asc())
        else:
            query = query.order_by(Location.name.desc())

        return self._paginate(query, page, page_size)

    # =========================================================
    # DRIVER PERFORMANCE
    # =========================================================

    def get_driver_performance(
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
        query = (
            self.db.query(
                Driver.id.label("driver_id"),
                User.full_name.label("driver_name"),
                func.count(
                    func.distinct(CollectionAssignment.id)
                ).label("total_assignments"),
                func.count(
                    func.distinct(
                        case(
                            (
                                CollectionAssignment.status
                                == AssignmentStatus.COMPLETED,
                                CollectionAssignment.id,
                            )
                        )
                    )
                ).label("completed_assignments"),
                func.coalesce(
                    func.sum(
                        CollectionTracking.collected_quantity_kg
                    ),
                    0,
                ).label("total_collected_kg"),
            )
            .join(User, User.id == Driver.user_id)
            .join(
                CollectionAssignment,
                CollectionAssignment.driver_id == Driver.id,
            )
            .join(
                Pickup,
                Pickup.id == CollectionAssignment.pickup_id,
            )
            .outerjoin(
                CollectionTracking,
                CollectionTracking.assignment_id
                == CollectionAssignment.id,
            )
        )

        query = self._apply_pickup_filters(
            query,
            start_date,
            end_date,
            zone_id,
            waste_category_id,
            status,
        )

        query = query.group_by(Driver.id, User.full_name)

        if sort_order.lower() == "asc":
            query = query.order_by(User.full_name.asc())
        else:
            query = query.order_by(User.full_name.desc())

        return self._paginate(query, page, page_size)

    # =========================================================
    # VEHICLE UTILIZATION
    # =========================================================

    def get_vehicle_utilization(
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
        query = (
            self.db.query(
                Vehicle.id.label("vehicle_id"),
                Vehicle.vehicle_code.label("vehicle_code"),
                Vehicle.registration_number.label(
                    "registration_number"
                ),
                func.count(
                    func.distinct(CollectionAssignment.id)
                ).label("total_assignments"),
                func.count(
                    func.distinct(
                        case(
                            (
                                CollectionAssignment.status
                                == AssignmentStatus.COMPLETED,
                                CollectionAssignment.id,
                            )
                        )
                    )
                ).label("completed_assignments"),
                func.coalesce(
                    func.sum(
                        CollectionTracking.collected_quantity_kg
                    ),
                    0,
                ).label("total_collected_kg"),
            )
            .join(
                CollectionAssignment,
                CollectionAssignment.vehicle_id == Vehicle.id,
            )
            .join(
                Pickup,
                Pickup.id == CollectionAssignment.pickup_id,
            )
            .outerjoin(
                CollectionTracking,
                CollectionTracking.assignment_id
                == CollectionAssignment.id,
            )
        )

        query = self._apply_pickup_filters(
            query,
            start_date,
            end_date,
            zone_id,
            waste_category_id,
            status,
        )

        query = query.group_by(
            Vehicle.id,
            Vehicle.vehicle_code,
            Vehicle.registration_number,
        )

        if sort_order.lower() == "asc":
            query = query.order_by(Vehicle.vehicle_code.asc())
        else:
            query = query.order_by(Vehicle.vehicle_code.desc())

        return self._paginate(query, page, page_size)

    # =========================================================
    # WASTE CATEGORY REPORTS
    # =========================================================

    def get_waste_category_reports(
        self,
        start_date=None,
        end_date=None,
        zone_id=None,
        waste_category_id=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        query = (
            self.db.query(
                WasteCategory.id.label("category_id"),
                WasteCategory.name.label("category_name"),
                func.coalesce(
                    func.sum(
                        WasteSegregation.incoming_quantity_kg
                    ),
                    0,
                ).label("total_quantity_kg"),
                func.coalesce(
                    func.sum(
                        WasteSegregation.recyclable_quantity_kg
                    ),
                    0,
                ).label("recyclable_quantity_kg"),
                func.coalesce(
                    func.sum(
                        WasteSegregation.non_recyclable_quantity_kg
                    ),
                    0,
                ).label("non_recyclable_quantity_kg"),
                func.coalesce(
                    func.sum(
                        WasteSegregation.contaminated_quantity_kg
                    ),
                    0,
                ).label("contaminated_quantity_kg"),
            )
            .join(
                WasteSegregation,
                WasteSegregation.waste_category_id
                == WasteCategory.id,
            )
        )

        if start_date:
            query = query.filter(
                WasteSegregation.created_at >= start_date
            )

        if end_date:
            query = query.filter(
                WasteSegregation.created_at <= end_date
            )

        if waste_category_id:
            query = query.filter(
                WasteCategory.id == waste_category_id
            )

        if zone_id:
            query = (
                query
                .join(
                    WasteTransfer,
                    WasteTransfer.id == WasteSegregation.transfer_id,
                )
                .filter(
                    WasteTransfer.source_location_id == zone_id
                )
            )

        query = query.group_by(
            WasteCategory.id,
            WasteCategory.name,
        )

        if sort_order.lower() == "asc":
            query = query.order_by(WasteCategory.name.asc())
        else:
            query = query.order_by(WasteCategory.name.desc())

        return self._paginate(query, page, page_size)

    # =========================================================
    # RECYCLING CENTER PERFORMANCE
    # =========================================================

    def get_recycling_center_performance(
        self,
        start_date=None,
        end_date=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        centers = self.db.query(RecyclingCenter).all()
        items = []

        for center in centers:
            transfer_query = self.db.query(
                func.coalesce(
                    func.sum(WasteTransfer.received_quantity_kg),
                    0,
                )
            ).filter(
                WasteTransfer.recycling_center_id == center.id,
                WasteTransfer.status.in_([
                    WasteTransferStatus.RECEIVED,
                    WasteTransferStatus.PARTIALLY_RECEIVED,
                ]),
            )

            processing_query = self.db.query(
                func.coalesce(
                    func.sum(
                        WasteProcessing.processing_quantity_kg
                    ),
                    0,
                ),
                func.coalesce(
                    func.sum(
                        WasteProcessing.output_quantity_kg
                    ),
                    0,
                ),
            ).filter(
                WasteProcessing.recycling_center_id == center.id
            )

            disposal_query = self.db.query(
                func.coalesce(
                    func.sum(
                        WasteDisposal.disposal_quantity_kg
                    ),
                    0,
                )
            ).filter(
                WasteDisposal.recycling_center_id == center.id
            )

            if start_date:
                transfer_query = transfer_query.filter(
                    WasteTransfer.created_at >= start_date
                )
                processing_query = processing_query.filter(
                    WasteProcessing.processed_at >= start_date
                )
                disposal_query = disposal_query.filter(
                    WasteDisposal.disposed_at >= start_date
                )

            if end_date:
                transfer_query = transfer_query.filter(
                    WasteTransfer.created_at <= end_date
                )
                processing_query = processing_query.filter(
                    WasteProcessing.processed_at <= end_date
                )
                disposal_query = disposal_query.filter(
                    WasteDisposal.disposed_at <= end_date
                )

            received = float(transfer_query.scalar() or 0)
            processed, recycled = processing_query.one()
            disposed = float(disposal_query.scalar() or 0)

            items.append({
                "recycling_center_id": str(center.id),
                "recycling_center_name": center.name,
                "total_received_kg": received,
                "total_processed_kg": float(processed or 0),
                "total_recycled_kg": float(recycled or 0),
                "total_disposed_kg": disposed,
            })

        items.sort(
            key=lambda item: item["total_received_kg"],
            reverse=sort_order.lower() != "asc",
        )

        total = len(items)
        page_size = max(1, min(page_size, 100))
        page = max(page, 1)
        start = (page - 1) * page_size

        return {
            "items": items[start:start + page_size],
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": ceil(total / page_size) if total else 0,
            },
        }

    # =========================================================
    # RECYCLING YIELD REPORT
    # =========================================================

    def get_recycling_yield_reports(
        self,
        start_date=None,
        end_date=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        query = (
            self.db.query(
                RecyclingCenter.id.label("recycling_center_id"),
                RecyclingCenter.name.label("recycling_center_name"),
                func.coalesce(
                    func.sum(
                        WasteProcessing.processing_quantity_kg
                    ),
                    0,
                ).label("input_quantity_kg"),
                func.coalesce(
                    func.sum(
                        WasteProcessing.output_quantity_kg
                    ),
                    0,
                ).label("output_quantity_kg"),
                func.coalesce(
                    func.sum(
                        WasteProcessing.residual_quantity_kg
                    ),
                    0,
                ).label("residual_quantity_kg"),
            )
            .join(
                WasteProcessing,
                WasteProcessing.recycling_center_id
                == RecyclingCenter.id,
            )
        )

        query = self._apply_date_filter(
            query,
            WasteProcessing.processed_at,
            start_date,
            end_date,
        )

        query = query.group_by(
            RecyclingCenter.id,
            RecyclingCenter.name,
        )

        if sort_order.lower() == "asc":
            query = query.order_by(RecyclingCenter.name.asc())
        else:
            query = query.order_by(RecyclingCenter.name.desc())

        return self._paginate(query, page, page_size)

    # =========================================================
    # DISPOSAL REPORTS
    # =========================================================

    def get_disposal_reports(
        self,
        start_date=None,
        end_date=None,
        waste_category_id=None,
        status=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        query = (
            self.db.query(
                WasteDisposal.id.label("disposal_id"),
                WasteDisposal.disposal_number.label(
                    "disposal_number"
                ),
                RecyclingCenter.name.label(
                    "recycling_center_name"
                ),
                WasteCategory.name.label(
                    "waste_category_name"
                ),
                WasteDisposal.disposal_method.label(
                    "disposal_method"
                ),
                WasteDisposal.disposal_quantity_kg.label(
                    "disposal_quantity_kg"
                ),
                WasteDisposal.status.label("status"),
            )
            .join(
                RecyclingCenter,
                RecyclingCenter.id
                == WasteDisposal.recycling_center_id,
            )
            .join(
                WasteCategory,
                WasteCategory.id == WasteDisposal.waste_category_id,
            )
        )

        query = self._apply_date_filter(
            query,
            WasteDisposal.disposed_at,
            start_date,
            end_date,
        )

        if waste_category_id:
            query = query.filter(
                WasteDisposal.waste_category_id == waste_category_id
            )

        if status:
            query = query.filter(WasteDisposal.status == status)

        if sort_order.lower() == "asc":
            query = query.order_by(WasteDisposal.disposed_at.asc())
        else:
            query = query.order_by(WasteDisposal.disposed_at.desc())

        return self._paginate(query, page, page_size)

    # =========================================================
    # ENVIRONMENTAL IMPACT REPORTS
    # =========================================================

    def get_environmental_impact_reports(
        self,
        start_date=None,
        end_date=None,
        page=1,
        page_size=20,
        sort_order="desc",
    ):
        query = self.db.query(
            EnvironmentalImpactSnapshot.period_start_date.label(
                "period_start_date"
            ),
            EnvironmentalImpactSnapshot.period_end_date.label(
                "period_end_date"
            ),
            EnvironmentalImpactSnapshot.total_waste_collected_kg.label(
                "total_waste_collected_kg"
            ),
            EnvironmentalImpactSnapshot.total_recyclable_waste_kg.label(
                "total_recyclable_waste_kg"
            ),
            EnvironmentalImpactSnapshot.total_waste_recycled_kg.label(
                "total_waste_recycled_kg"
            ),
            EnvironmentalImpactSnapshot.total_waste_disposed_kg.label(
                "total_waste_disposed_kg"
            ),
            EnvironmentalImpactSnapshot.recycling_rate_percentage.label(
                "recycling_rate_percentage"
            ),
        )

        if start_date:
            query = query.filter(
                EnvironmentalImpactSnapshot.period_start_date
                >= start_date
            )

        if end_date:
            query = query.filter(
                EnvironmentalImpactSnapshot.period_end_date
                <= end_date
            )

        if sort_order.lower() == "asc":
            query = query.order_by(
                EnvironmentalImpactSnapshot.period_start_date.asc()
            )
        else:
            query = query.order_by(
                EnvironmentalImpactSnapshot.period_start_date.desc()
            )

        return self._paginate(query, page, page_size)
