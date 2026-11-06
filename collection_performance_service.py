from datetime import date, timezone
from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import (
    PickupStatus,
    CollectionTrackingStatus,
    LocationType,
    VehicleStatus,
)

from repositories.collection_performance_repository import (
    CollectionPerformanceRepository,
)

from schemas.collection_performance import (
    CollectionPerformanceSummary,
    ZoneCollectionPerformance,
    DriverCollectionPerformance,
    VehicleCollectionPerformance,
)


class CollectionPerformanceService:

    @staticmethod
    def validate_dates(start_date, end_date):
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_date cannot be later than end_date",
            )

    @staticmethod
    def get_data(db, start_date=None, end_date=None):
        CollectionPerformanceService.validate_dates(
            start_date,
            end_date,
        )

        pickups = CollectionPerformanceRepository.get_pickups(
            db,
            start_date,
            end_date,
        )

        trackings = CollectionPerformanceRepository.get_trackings(
            db,
            start_date,
            end_date,
        )

        assignments = CollectionPerformanceRepository.get_assignments(
            db,
            start_date,
            end_date,
        )

        return pickups, trackings, assignments

    @staticmethod
    def get_tracking_duration_minutes(tracking):
        if not tracking.started_at or not tracking.completed_at:
            return None

        started = tracking.started_at
        completed = tracking.completed_at

        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)

        if completed.tzinfo is None:
            completed = completed.replace(tzinfo=timezone.utc)

        duration = (completed - started).total_seconds()

        if duration < 0:
            return None

        return duration / 60

    @staticmethod
    def average_duration(trackings):
        durations = []

        for tracking in trackings:
            if tracking.status not in (
                CollectionTrackingStatus.COMPLETED,
                CollectionTrackingStatus.PARTIALLY_COMPLETED,
            ):
                continue

            duration = (
                CollectionPerformanceService
                .get_tracking_duration_minutes(tracking)
            )

            if duration is not None:
                durations.append(duration)

        if not durations:
            return 0.0

        return round(sum(durations) / len(durations), 2)

    @staticmethod
    def get_summary(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        pickups, trackings, assignments = (
            CollectionPerformanceService.get_data(
                db,
                start_date,
                end_date,
            )
        )

        total_pickups = len(pickups)

        completed_pickups = sum(
            1 for pickup in pickups
            if pickup.status == PickupStatus.COMPLETED
        )

        missed_pickup_ids = {
            tracking.pickup_id
            for tracking in trackings
            if tracking.status == CollectionTrackingStatus.FAILED
        }

        missed_pickups = len(missed_pickup_ids)

        efficiency = (
            completed_pickups / total_pickups * 100
            if total_pickups
            else 0.0
        )

        vehicles = CollectionPerformanceRepository.get_vehicles(db)

        active_vehicles = [
            vehicle for vehicle in vehicles
            if vehicle.status != VehicleStatus.RETIRED
        ]

        utilized_vehicle_ids = {
            assignment.vehicle_id
            for assignment in assignments
        }

        utilized_vehicles = sum(
            1 for vehicle in active_vehicles
            if vehicle.id in utilized_vehicle_ids
        )

        utilization = (
            utilized_vehicles / len(active_vehicles) * 100
            if active_vehicles
            else 0.0
        )

        return CollectionPerformanceSummary(
            start_date=start_date,
            end_date=end_date,
            total_pickup_requests=total_pickups,
            completed_pickups=completed_pickups,
            missed_pickups=missed_pickups,
            average_collection_time_minutes=(
                CollectionPerformanceService.average_duration(
                    trackings
                )
            ),
            collection_efficiency_percentage=round(efficiency, 2),
            active_vehicles=len(active_vehicles),
            utilized_vehicles=utilized_vehicles,
            vehicle_utilization_percentage=round(utilization, 2),
        )

    @staticmethod
    def get_zone_performance(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        pickups, trackings, _ = (
            CollectionPerformanceService.get_data(
                db,
                start_date,
                end_date,
            )
        )

        locations = CollectionPerformanceRepository.get_locations(db)

        location_map = {
            location.id: location
            for location in locations
        }

        def find_zone(location_id):
            visited = set()
            current = location_map.get(location_id)

            while current and current.id not in visited:
                visited.add(current.id)

                if current.location_type == LocationType.ZONE:
                    return current

                current = location_map.get(current.parent_id)

            return None

        failed_pickup_ids = {
            tracking.pickup_id
            for tracking in trackings
            if tracking.status == CollectionTrackingStatus.FAILED
        }

        results = defaultdict(
            lambda: {
                "total": 0,
                "completed": 0,
                "missed": 0,
            }
        )

        zone_objects = {}

        for pickup in pickups:
            zone = find_zone(pickup.location_id)

            if zone:
                key = zone.id
                zone_objects[key] = zone
            else:
                key = None

            results[key]["total"] += 1

            if pickup.status == PickupStatus.COMPLETED:
                results[key]["completed"] += 1

            if pickup.id in failed_pickup_ids:
                results[key]["missed"] += 1

        response = []

        for zone_id, values in results.items():
            total = values["total"]

            efficiency = (
                values["completed"] / total * 100
                if total
                else 0.0
            )

            zone = zone_objects.get(zone_id)

            response.append(
                ZoneCollectionPerformance(
                    zone_id=zone_id,
                    zone_name=zone.name if zone else "Unassigned",
                    total_pickups=total,
                    completed_pickups=values["completed"],
                    missed_pickups=values["missed"],
                    collection_efficiency_percentage=round(
                        efficiency,
                        2,
                    ),
                )
            )

        return sorted(
            response,
            key=lambda item: item.total_pickups,
            reverse=True,
        )

    @staticmethod
    def get_driver_performance(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        pickups, trackings, assignments = (
            CollectionPerformanceService.get_data(
                db,
                start_date,
                end_date,
            )
        )

        drivers = CollectionPerformanceRepository.get_drivers(db)

        driver_map = {
            driver.id: driver
            for driver in drivers
        }

        pickup_map = {
            pickup.id: pickup
            for pickup in pickups
        }

        tracking_map = {
            tracking.assignment_id: tracking
            for tracking in trackings
        }

        results = defaultdict(
            lambda: {
                "total": 0,
                "completed": 0,
                "missed": 0,
                "durations": [],
            }
        )

        for assignment in assignments:
            driver_id = assignment.driver_id

            results[driver_id]["total"] += 1

            pickup = pickup_map.get(assignment.pickup_id)

            if pickup and pickup.status == PickupStatus.COMPLETED:
                results[driver_id]["completed"] += 1

            tracking = tracking_map.get(assignment.id)

            if tracking:
                if tracking.status == CollectionTrackingStatus.FAILED:
                    results[driver_id]["missed"] += 1

                duration = (
                    CollectionPerformanceService
                    .get_tracking_duration_minutes(tracking)
                )

                if (
                    duration is not None
                    and tracking.status in (
                        CollectionTrackingStatus.COMPLETED,
                        CollectionTrackingStatus.PARTIALLY_COMPLETED,
                    )
                ):
                    results[driver_id]["durations"].append(duration)

        response = []

        for driver_id, values in results.items():
            driver = driver_map.get(driver_id)

            if not driver:
                continue

            durations = values["durations"]

            response.append(
                DriverCollectionPerformance(
                    driver_id=driver.id,
                    driver_code=driver.driver_code,
                    total_assignments=values["total"],
                    completed_pickups=values["completed"],
                    missed_pickups=values["missed"],
                    average_collection_time_minutes=round(
                        sum(durations) / len(durations),
                        2,
                    ) if durations else 0.0,
                )
            )

        return sorted(
            response,
            key=lambda item: item.total_assignments,
            reverse=True,
        )

    @staticmethod
    def get_vehicle_performance(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        pickups, trackings, assignments = (
            CollectionPerformanceService.get_data(
                db,
                start_date,
                end_date,
            )
        )

        vehicles = CollectionPerformanceRepository.get_vehicles(db)

        pickup_map = {
            pickup.id: pickup
            for pickup in pickups
        }

        tracking_map = {
            tracking.assignment_id: tracking
            for tracking in trackings
        }

        results = defaultdict(
            lambda: {
                "total": 0,
                "completed": 0,
                "missed": 0,
            }
        )

        for assignment in assignments:
            vehicle_id = assignment.vehicle_id

            results[vehicle_id]["total"] += 1

            pickup = pickup_map.get(assignment.pickup_id)

            if pickup and pickup.status == PickupStatus.COMPLETED:
                results[vehicle_id]["completed"] += 1

            tracking = tracking_map.get(assignment.id)

            if (
                tracking
                and tracking.status == CollectionTrackingStatus.FAILED
            ):
                results[vehicle_id]["missed"] += 1

        response = []

        for vehicle in vehicles:
            values = results[vehicle.id]

            response.append(
                VehicleCollectionPerformance(
                    vehicle_id=vehicle.id,
                    vehicle_code=vehicle.vehicle_code,
                    registration_number=vehicle.registration_number,
                    total_assignments=values["total"],
                    completed_pickups=values["completed"],
                    missed_pickups=values["missed"],
                    is_utilized=values["total"] > 0,
                )
            )

        return sorted(
            response,
            key=lambda item: item.total_assignments,
            reverse=True,
        )