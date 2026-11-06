
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from models.collection_tracking import CollectionTracking
from models.waste_category import WasteCategory
from models.waste_segregation import WasteSegregation
from models.waste_processing import WasteProcessing
from models.waste_disposal import WasteDisposal
from models.environmental_impact import EnvironmentalImpactSnapshot


class EnvironmentalImpactRepository:

    @staticmethod
    def _apply_date_filter(query, column, start_date, end_date):
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
    def get_collection_trackings(db: Session, start_date=None, end_date=None):
        query = db.query(CollectionTracking).filter(
            CollectionTracking.status.in_(
                ["completed", "partially_completed"]
            )
        )

        return EnvironmentalImpactRepository._apply_date_filter(
            query,
            CollectionTracking.completed_at,
            start_date,
            end_date,
        ).all()

    @staticmethod
    def get_segregations(db: Session, start_date=None, end_date=None):
        query = db.query(WasteSegregation)

        return EnvironmentalImpactRepository._apply_date_filter(
            query,
            WasteSegregation.segregated_at,
            start_date,
            end_date,
        ).all()

    @staticmethod
    def get_processings(db: Session, start_date=None, end_date=None):
        query = db.query(WasteProcessing)

        return EnvironmentalImpactRepository._apply_date_filter(
            query,
            WasteProcessing.processed_at,
            start_date,
            end_date,
        ).all()

    @staticmethod
    def get_disposals(db: Session, start_date=None, end_date=None):
        query = db.query(WasteDisposal)

        return EnvironmentalImpactRepository._apply_date_filter(
            query,
            WasteDisposal.disposed_at,
            start_date,
            end_date,
        ).all()

    @staticmethod
    def get_categories(db: Session):
        return db.query(WasteCategory).all()

    @staticmethod
    def create_snapshot(db: Session, snapshot):
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    @staticmethod
    def get_snapshots(db: Session):
        return (
            db.query(EnvironmentalImpactSnapshot)
            .order_by(EnvironmentalImpactSnapshot.generated_at.desc())
            .all()
        )

    @staticmethod
    def get_snapshot_by_id(db: Session, snapshot_id):
        return (
            db.query(EnvironmentalImpactSnapshot)
            .filter(EnvironmentalImpactSnapshot.id == snapshot_id)
            .first()
        )
