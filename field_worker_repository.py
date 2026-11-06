
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.field_worker import FieldWorker


class FieldWorkerRepository:

    @staticmethod
    def create(db: Session, worker: FieldWorker) -> FieldWorker:
        db.add(worker)
        db.commit()
        db.refresh(worker)
        return worker

    @staticmethod
    def get_by_id(db: Session, worker_id: UUID) -> FieldWorker | None:
        return db.scalar(
            select(FieldWorker).where(FieldWorker.id == worker_id)
        )

    @staticmethod
    def get_by_user_id(db: Session, user_id: UUID) -> FieldWorker | None:
        return db.scalar(
            select(FieldWorker).where(FieldWorker.user_id == user_id)
        )

    @staticmethod
    def get_by_code(db: Session, worker_code: str) -> FieldWorker | None:
        return db.scalar(
            select(FieldWorker).where(FieldWorker.worker_code == worker_code)
        )

    @staticmethod
    def list_all(
        db: Session,
        status=None,
        availability=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FieldWorker]:
        query = select(FieldWorker)

        if status is not None:
            query = query.where(FieldWorker.status == status)

        if availability is not None:
            query = query.where(FieldWorker.availability == availability)

        query = query.order_by(FieldWorker.created_at.desc())
        query = query.offset(skip).limit(limit)

        return list(db.scalars(query).all())

    @staticmethod
    def update(db: Session, worker: FieldWorker) -> FieldWorker:
        db.commit()
        db.refresh(worker)
        return worker

    @staticmethod
    def delete(db: Session, worker: FieldWorker) -> None:
        db.delete(worker)
        db.commit()
