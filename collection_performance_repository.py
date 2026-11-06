from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from models.pickup import Pickup
from models.collection_tracking import CollectionTracking
from models.collection_assignment import CollectionAssignment
from models.vehicle import Vehicle
from models.driver import Driver
from models.location import Location


class CollectionPerformanceRepository:

    @staticmethod
    def _apply_datetime_filter(query, column, start_date, end_date):
        if start_date:
            start_datetime = datetime.combine(
                start_date,
                time.min,
                tzinfo=timezone.utc,
            )
            query = query.filter(column >= start_datetime)

        if end_date:
            end_datetime = datetime.combine(
                end_date + timedelta(days=1),
                time.min,
                tzinfo=timezone.utc,
            )
            query = query.filter(column < end_datetime)

        return query

    @staticmethod
    def get_pickups(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        query = db.query(Pickup)

        query = (
            CollectionPerformanceRepository
            ._apply_datetime_filter(
                query,
                Pickup.requested_at,
                start_date,
                end_date,
            )
        )

        return query.all()

    @staticmethod
    def get_trackings(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        query = db.query(CollectionTracking)

        query = (
            CollectionPerformanceRepository
            ._apply_datetime_filter(
                query,
                CollectionTracking.started_at,
                start_date,
                end_date,
            )
        )

        return query.all()

    @staticmethod
    def get_assignments(
        db: Session,
        start_date: date | None = None,
        end_date: date | None = None,
    ):
        query = db.query(CollectionAssignment)

        if start_date:
            query = query.filter(
                CollectionAssignment.scheduled_date >= start_date
            )

        if end_date:
            query = query.filter(
                CollectionAssignment.scheduled_date <= end_date
            )

        return query.all()

    @staticmethod
    def get_vehicles(db: Session):
        return (
            db.query(Vehicle)
            .filter(Vehicle.is_active.is_(True))
            .all()
        )

    @staticmethod
    def get_drivers(db: Session):
        return db.query(Driver).all()

    @staticmethod
    def get_locations(db: Session):
        return db.query(Location).all()