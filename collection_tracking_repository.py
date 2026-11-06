
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.collection_tracking import CollectionTracking
from core.constants import CollectionTrackingStatus


class CollectionTrackingRepository:

    @staticmethod
    def create(
        db: Session,
        tracking: CollectionTracking,
    ) -> CollectionTracking:
        db.add(tracking)
        db.commit()
        db.refresh(tracking)
        return tracking

    @staticmethod
    def get_by_id(
        db: Session,
        tracking_id: UUID,
    ) -> CollectionTracking | None:
        return db.scalar(
            select(CollectionTracking).where(
                CollectionTracking.id == tracking_id
            )
        )

    @staticmethod
    def get_by_code(
        db: Session,
        tracking_code: str,
    ) -> CollectionTracking | None:
        return db.scalar(
            select(CollectionTracking).where(
                CollectionTracking.tracking_code == tracking_code
            )
        )

    @staticmethod
    def get_by_assignment(
        db: Session,
        assignment_id: UUID,
    ) -> CollectionTracking | None:
        return db.scalar(
            select(CollectionTracking).where(
                CollectionTracking.assignment_id == assignment_id
            )
        )

    @staticmethod
    def get_by_pickup(
        db: Session,
        pickup_id: UUID,
    ) -> list[CollectionTracking]:
        statement = (
            select(CollectionTracking)
            .where(CollectionTracking.pickup_id == pickup_id)
            .order_by(CollectionTracking.created_at.desc())
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def list_all(
        db: Session,
        status: CollectionTrackingStatus | None = None,
        pickup_id: UUID | None = None,
        assignment_id: UUID | None = None,
    ) -> list[CollectionTracking]:
        statement = select(CollectionTracking)

        if status is not None:
            statement = statement.where(
                CollectionTracking.status == status
            )

        if pickup_id is not None:
            statement = statement.where(
                CollectionTracking.pickup_id == pickup_id
            )

        if assignment_id is not None:
            statement = statement.where(
                CollectionTracking.assignment_id == assignment_id
            )

        statement = statement.order_by(
            CollectionTracking.created_at.desc()
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def update(
        db: Session,
        tracking: CollectionTracking,
        update_data: dict,
    ) -> CollectionTracking:
        for key, value in update_data.items():
            setattr(tracking, key, value)

        db.commit()
        db.refresh(tracking)
        return tracking

    @staticmethod
    def update_status(
        db: Session,
        tracking: CollectionTracking,
        status: CollectionTrackingStatus,
    ) -> CollectionTracking:
        tracking.status = status

        db.commit()
        db.refresh(tracking)
        return tracking
