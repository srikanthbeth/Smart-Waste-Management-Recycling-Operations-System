
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.constants import (
    AssignmentStatus,
    CollectionTrackingStatus,
    PickupStatus,
)
from models.collection_tracking import CollectionTracking
from models.collection_assignment import CollectionAssignment
from models.pickup import Pickup
from models.driver import Driver
from models.field_worker import FieldWorker
from models.vehicle import Vehicle

from repositories.collection_tracking_repository import (
    CollectionTrackingRepository,
)

from schemas.collection_tracking import (
    CollectionTrackingCreate,
    CollectionTrackingUpdate,
    CollectionTrackingStatusUpdate,
)


class CollectionTrackingService:

    @staticmethod
    def _get_assignment(db: Session, assignment_id: UUID):
        assignment = db.get(CollectionAssignment, assignment_id)

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection assignment not found",
            )

        return assignment

    @staticmethod
    def _get_tracking(db: Session, tracking_id: UUID):
        tracking = CollectionTrackingRepository.get_by_id(
            db,
            tracking_id,
        )

        if not tracking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection tracking record not found",
            )

        return tracking

    @staticmethod
    def _verify_assigned_staff(
        db: Session,
        assignment: CollectionAssignment,
        current_user,
    ):
        is_assigned_driver = db.scalar(
            select(Driver.id).where(
                Driver.id == assignment.driver_id,
                Driver.user_id == current_user.id,
            )
        ) is not None

        is_assigned_worker = any(
            worker.user_id == current_user.id
            for worker in assignment.field_workers
        )

        if not is_assigned_driver and not is_assigned_worker:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Only assigned drivers or field workers "
                    "can perform this action"
                ),
            )

    @staticmethod
    def _validate_quantity(
        db: Session,
        quantity,
        pickup: Pickup,
        assignment: CollectionAssignment,
        partial: bool = False,
    ):
        if quantity is None or quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Collected quantity must be greater than zero",
            )

        estimated_quantity = pickup.estimated_quantity_kg

        if (
            estimated_quantity is not None
            and quantity > estimated_quantity
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Collected quantity cannot exceed "
                    "the requested quantity"
                ),
            )

        vehicle = db.get(Vehicle, assignment.vehicle_id)

        if vehicle is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned vehicle not found",
            )

        if quantity > vehicle.capacity_kg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Collected quantity cannot exceed vehicle capacity",
            )

        if (
            partial
            and estimated_quantity is not None
            and quantity >= estimated_quantity
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Partially completed quantity must be less "
                    "than requested quantity"
                ),
            )

    @staticmethod
    def start_tracking(
        db: Session,
        data: CollectionTrackingCreate,
        current_user,
    ):
        assignment = CollectionTrackingService._get_assignment(
            db,
            data.assignment_id,
        )

        CollectionTrackingService._verify_assigned_staff(
            db,
            assignment,
            current_user,
        )

        # Check for existing tracking before checking assignment status.
        existing = CollectionTrackingRepository.get_by_assignment(
            db,
            assignment.id,
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tracking already exists for this assignment",
            )

        if assignment.status != AssignmentStatus.ASSIGNED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only assigned collections can be started",
            )

        pickup = db.get(Pickup, assignment.pickup_id)

        if not pickup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pickup not found",
            )

        now = datetime.now(timezone.utc)

        tracking = CollectionTracking(
            tracking_code=f"TRK-{uuid4().hex[:12].upper()}",
            assignment_id=assignment.id,
            pickup_id=pickup.id,
            tracked_by_user_id=current_user.id,
            status=CollectionTrackingStatus.IN_PROGRESS,
            started_at=now,
            remarks=data.remarks,
            photo_urls=data.photo_urls,
        )

        assignment.status = AssignmentStatus.IN_PROGRESS
        assignment.started_at = now

        pickup.status = PickupStatus.IN_PROGRESS

        db.add(assignment)
        db.add(pickup)

        try:
            return CollectionTrackingRepository.create(
                db,
                tracking,
            )
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_tracking(
        db: Session,
        tracking_id: UUID,
    ):
        return CollectionTrackingService._get_tracking(
            db,
            tracking_id,
        )

    @staticmethod
    def list_trackings(
        db: Session,
        tracking_status=None,
        pickup_id=None,
        assignment_id=None,
    ):
        return CollectionTrackingRepository.list_all(
            db,
            status=tracking_status,
            pickup_id=pickup_id,
            assignment_id=assignment_id,
        )

    @staticmethod
    def get_pickup_tracking_history(
        db: Session,
        pickup_id: UUID,
    ):
        pickup = db.get(Pickup, pickup_id)

        if not pickup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pickup not found",
            )

        return CollectionTrackingRepository.get_by_pickup(
            db,
            pickup_id,
        )

    @staticmethod
    def update_tracking(
        db: Session,
        tracking_id: UUID,
        data: CollectionTrackingUpdate,
        current_user,
    ):
        tracking = CollectionTrackingService._get_tracking(
            db,
            tracking_id,
        )

        assignment = CollectionTrackingService._get_assignment(
            db,
            tracking.assignment_id,
        )

        CollectionTrackingService._verify_assigned_staff(
            db,
            assignment,
            current_user,
        )

        if tracking.status != CollectionTrackingStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only in-progress tracking records can be updated",
            )

        update_data = data.model_dump(exclude_unset=True)

        if "collected_quantity_kg" in update_data:
            pickup = db.get(Pickup, tracking.pickup_id)

            if not pickup:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pickup not found",
                )

            CollectionTrackingService._validate_quantity(
                db,
                update_data["collected_quantity_kg"],
                pickup,
                assignment,
            )

        return CollectionTrackingRepository.update(
            db,
            tracking,
            update_data,
        )

    @staticmethod
    def update_tracking_status(
        db: Session,
        tracking_id: UUID,
        data: CollectionTrackingStatusUpdate,
        current_user,
    ):
        tracking = CollectionTrackingService._get_tracking(
            db,
            tracking_id,
        )

        assignment = CollectionTrackingService._get_assignment(
            db,
            tracking.assignment_id,
        )

        CollectionTrackingService._verify_assigned_staff(
            db,
            assignment,
            current_user,
        )

        if tracking.status != CollectionTrackingStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Only in-progress tracking records "
                    "can change status"
                ),
            )

        if data.status == CollectionTrackingStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tracking is already in progress",
            )

        if data.status not in (
            CollectionTrackingStatus.COMPLETED,
            CollectionTrackingStatus.PARTIALLY_COMPLETED,
            CollectionTrackingStatus.FAILED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tracking status transition",
            )

        pickup = db.get(Pickup, tracking.pickup_id)

        if not pickup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pickup not found",
            )

        if data.status in (
            CollectionTrackingStatus.COMPLETED,
            CollectionTrackingStatus.PARTIALLY_COMPLETED,
        ):
            CollectionTrackingService._validate_quantity(
                db,
                data.collected_quantity_kg,
                pickup,
                assignment,
                partial=(
                    data.status
                    == CollectionTrackingStatus.PARTIALLY_COMPLETED
                ),
            )

        if (
            data.status == CollectionTrackingStatus.FAILED
            and not data.remarks
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remarks are required for failed collections",
            )

        now = datetime.now(timezone.utc)

        tracking.status = data.status
        tracking.collected_quantity_kg = data.collected_quantity_kg
        tracking.remarks = data.remarks or tracking.remarks
        tracking.completed_at = now

        if data.status in (
            CollectionTrackingStatus.COMPLETED,
            CollectionTrackingStatus.PARTIALLY_COMPLETED,
        ):
            assignment.status = AssignmentStatus.COMPLETED
            assignment.completed_at = now
            pickup.status = PickupStatus.COMPLETED

        elif data.status == CollectionTrackingStatus.FAILED:
            assignment.status = AssignmentStatus.CANCELLED
            assignment.cancelled_at = now
            assignment.cancellation_reason = data.remarks
            pickup.status = PickupStatus.CANCELLED

        db.add(assignment)
        db.add(pickup)

        try:
            return CollectionTrackingRepository.update(
                db,
                tracking,
                {
                    "status": tracking.status,
                    "collected_quantity_kg": tracking.collected_quantity_kg,
                    "remarks": tracking.remarks,
                    "completed_at": tracking.completed_at,
                },
            )
        except Exception:
            db.rollback()
            raise
