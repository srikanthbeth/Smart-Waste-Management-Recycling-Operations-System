from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.collection_assignment import (
    CollectionAssignment,
    collection_assignment_field_workers,
)
from models.driver import Driver
from models.field_worker import FieldWorker


class CollectionAssignmentRepository:

    @staticmethod
    def create(
        db: Session,
        assignment: CollectionAssignment,
        field_worker_ids: list[UUID],
    ) -> CollectionAssignment:

        db.add(assignment)
        db.flush()

        if field_worker_ids:
            workers = db.scalars(
                select(FieldWorker).where(
                    FieldWorker.id.in_(field_worker_ids)
                )
            ).all()

            assignment.field_workers = workers

        db.commit()
        db.refresh(assignment)

        return assignment

    @staticmethod
    def get_by_id(
        db: Session,
        assignment_id: UUID,
    ) -> Optional[CollectionAssignment]:

        return db.scalar(
            select(CollectionAssignment)
            .options(
                selectinload(CollectionAssignment.field_workers)
            )
            .where(CollectionAssignment.id == assignment_id)
        )

    @staticmethod
    def get_by_code(
        db: Session,
        assignment_code: str,
    ) -> Optional[CollectionAssignment]:

        return db.scalar(
            select(CollectionAssignment)
            .where(
                CollectionAssignment.assignment_code == assignment_code
            )
        )

    @staticmethod
    def get_active_by_pickup(
        db: Session,
        pickup_id: UUID,
    ) -> Optional[CollectionAssignment]:

        return db.scalar(
            select(CollectionAssignment)
            .where(
                CollectionAssignment.pickup_id == pickup_id,
                CollectionAssignment.status.in_([
                    "assigned",
                    "in_progress",
                ]),
            )
        )

    @staticmethod
    def get_active_by_driver(
        db: Session,
        driver_id: UUID,
    ) -> Optional[CollectionAssignment]:

        return db.scalar(
            select(CollectionAssignment)
            .where(
                CollectionAssignment.driver_id == driver_id,
                CollectionAssignment.status.in_([
                    "assigned",
                    "in_progress",
                ]),
            )
        )

    @staticmethod
    def get_active_by_vehicle(
        db: Session,
        vehicle_id: UUID,
    ) -> Optional[CollectionAssignment]:

        return db.scalar(
            select(CollectionAssignment)
            .where(
                CollectionAssignment.vehicle_id == vehicle_id,
                CollectionAssignment.status.in_([
                    "assigned",
                    "in_progress",
                ]),
            )
        )

    @staticmethod
    def list_all(
        db: Session,
        status: Optional[str] = None,
        driver_id: Optional[UUID] = None,
        vehicle_id: Optional[UUID] = None,
        pickup_id: Optional[UUID] = None,
    ) -> list[CollectionAssignment]:

        query = (
            select(CollectionAssignment)
            .options(
                selectinload(CollectionAssignment.field_workers)
            )
        )

        if status:
            query = query.where(
                CollectionAssignment.status == status
            )

        if driver_id:
            query = query.where(
                CollectionAssignment.driver_id == driver_id
            )

        if vehicle_id:
            query = query.where(
                CollectionAssignment.vehicle_id == vehicle_id
            )

        if pickup_id:
            query = query.where(
                CollectionAssignment.pickup_id == pickup_id
            )

        query = query.order_by(
            CollectionAssignment.created_at.desc()
        )

        return list(db.scalars(query).all())

    @staticmethod
    def update(
        db: Session,
        assignment: CollectionAssignment,
        update_data: dict,
        field_worker_ids: Optional[list[UUID]] = None,
    ) -> CollectionAssignment:

        for key, value in update_data.items():
            setattr(assignment, key, value)

        if field_worker_ids is not None:
            workers = db.scalars(
                select(FieldWorker).where(
                    FieldWorker.id.in_(field_worker_ids)
                )
            ).all()

            assignment.field_workers = workers

        db.commit()
        db.refresh(assignment)

        return assignment

    @staticmethod
    def update_status(
        db: Session,
        assignment: CollectionAssignment,
        status,
        cancellation_reason: Optional[str] = None,
    ) -> CollectionAssignment:

        assignment.status = status
        assignment.cancellation_reason = cancellation_reason

        db.commit()
        db.refresh(assignment)

        return assignment

    @staticmethod
    def delete(
        db: Session,
        assignment: CollectionAssignment,
    ) -> None:

        db.delete(assignment)
        db.commit()