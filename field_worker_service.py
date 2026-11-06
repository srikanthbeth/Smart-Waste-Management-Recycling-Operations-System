
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.field_worker import FieldWorker
from models.user import User
from schemas.field_worker import (
    FieldWorkerCreate,
    FieldWorkerUpdate,
    FieldWorkerStatusUpdate,
)
from repositories.field_worker_repository import FieldWorkerRepository


class FieldWorkerService:

    @staticmethod
    def create_worker(db: Session, data: FieldWorkerCreate) -> FieldWorker:
        user = db.get(User, data.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        role = user.role.value if hasattr(user.role, "value") else str(user.role)

        if role.lower() not in {"field_worker", "field worker"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected user must have the Field Worker role",
            )

        if FieldWorkerRepository.get_by_user_id(db, data.user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user already has a field worker profile",
            )

        if FieldWorkerRepository.get_by_code(db, data.worker_code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Worker code already exists",
            )

        worker = FieldWorker(**data.model_dump())
        return FieldWorkerRepository.create(db, worker)

    @staticmethod
    def get_worker(db: Session, worker_id: UUID) -> FieldWorker:
        worker = FieldWorkerRepository.get_by_id(db, worker_id)

        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Field worker not found",
            )

        return worker

    @staticmethod
    def get_my_profile(db: Session, user_id: UUID) -> FieldWorker:
        worker = FieldWorkerRepository.get_by_user_id(db, user_id)

        if not worker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Field worker profile not found",
            )

        return worker

    @staticmethod
    def list_workers(
        db: Session,
        status_filter=None,
        availability=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FieldWorker]:
        return FieldWorkerRepository.list_all(
            db,
            status=status_filter,
            availability=availability,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def update_worker(
        db: Session,
        worker_id: UUID,
        data: FieldWorkerUpdate,
    ) -> FieldWorker:
        worker = FieldWorkerService.get_worker(db, worker_id)

        changes = data.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided",
            )

        if worker.status.value == "retired":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Retired field workers cannot be updated",
            )

        for key, value in changes.items():
            setattr(worker, key, value)

        return FieldWorkerRepository.update(db, worker)

    @staticmethod
    def update_status(
        db: Session,
        worker_id: UUID,
        data: FieldWorkerStatusUpdate,
    ) -> FieldWorker:
        worker = FieldWorkerService.get_worker(db, worker_id)

        if worker.status.value == "retired":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Retired field worker status cannot be changed",
            )

        worker.status = data.status

        if data.availability is not None:
            worker.availability = data.availability

        if data.status in {
            worker.status.__class__.INACTIVE,
            worker.status.__class__.SUSPENDED,
            worker.status.__class__.ON_LEAVE,
        }:
            worker.availability = worker.availability.__class__.UNAVAILABLE

        return FieldWorkerRepository.update(db, worker)
