
from datetime import datetime, timezone
from uuid import uuid4, UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.constants import (
    AssignmentStatus,
    PickupStatus,
    VehicleStatus,
    StaffStatus,
    StaffAvailability,
)

from models.collection_assignment import (
    CollectionAssignment,
    collection_assignment_field_workers,
)
from models.pickup import Pickup
from models.driver import Driver
from models.vehicle import Vehicle
from models.field_worker import FieldWorker

from repositories.collection_assignment_repository import (
    CollectionAssignmentRepository,
)


class CollectionAssignmentService:

    ACTIVE_ASSIGNMENT_STATUSES = [
        AssignmentStatus.ASSIGNED,
        AssignmentStatus.IN_PROGRESS,
    ]

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    # ---------------------------------------------------------
    # CREATE COLLECTION ASSIGNMENT
    # ---------------------------------------------------------

    @staticmethod
    def create_assignment(
        db: Session,
        data,
        assigned_by_user_id: UUID,
    ) -> CollectionAssignment:

        # 1. Validate pickup exists
        pickup = db.get(Pickup, data.pickup_id)

        if not pickup:
            raise HTTPException(
                status_code=404,
                detail="Pickup not found",
            )

        # 2. Check existing active assignment FIRST
        existing = CollectionAssignmentRepository.get_active_by_pickup(
            db,
            data.pickup_id,
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail="Pickup already has an active assignment",
            )

        # 3. Validate pickup status
        if pickup.status not in [
            PickupStatus.APPROVED,
            PickupStatus.SCHEDULED,
        ]:
            raise HTTPException(
                status_code=400,
                detail="Pickup must be approved or scheduled",
            )

        # 4. Validate driver
        driver = db.get(Driver, data.driver_id)

        if not driver:
            raise HTTPException(
                status_code=404,
                detail="Driver not found",
            )

        if driver.status != StaffStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail="Driver is not active",
            )

        if driver.availability != StaffAvailability.AVAILABLE:
            raise HTTPException(
                status_code=400,
                detail="Driver is not available",
            )

        if CollectionAssignmentRepository.get_active_by_driver(
            db,
            data.driver_id,
        ):
            raise HTTPException(
                status_code=400,
                detail="Driver already has an active assignment",
            )

        # 5. Validate vehicle
        vehicle = db.get(Vehicle, data.vehicle_id)

        if not vehicle:
            raise HTTPException(
                status_code=404,
                detail="Vehicle not found",
            )

        if not vehicle.is_active:
            raise HTTPException(
                status_code=400,
                detail="Vehicle is inactive",
            )

        if vehicle.status != VehicleStatus.AVAILABLE:
            raise HTTPException(
                status_code=400,
                detail="Vehicle is not available",
            )

        if vehicle.capacity_kg < pickup.estimated_quantity_kg:
            raise HTTPException(
                status_code=400,
                detail="Vehicle capacity is insufficient for this pickup",
            )

        if CollectionAssignmentRepository.get_active_by_vehicle(
            db,
            data.vehicle_id,
        ):
            raise HTTPException(
                status_code=400,
                detail="Vehicle already has an active assignment",
            )

        # 6. Validate field workers
        workers = []

        if data.field_worker_ids:
            workers = db.scalars(
                select(FieldWorker).where(
                    FieldWorker.id.in_(data.field_worker_ids)
                )
            ).all()

            if len(workers) != len(data.field_worker_ids):
                raise HTTPException(
                    status_code=404,
                    detail="One or more field workers were not found",
                )

            for worker in workers:

                if worker.status != StaffStatus.ACTIVE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field worker {worker.worker_code} is not active",
                    )

                if worker.availability != StaffAvailability.AVAILABLE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field worker {worker.worker_code} is not available",
                    )

                existing_worker_assignment = db.scalar(
                    select(CollectionAssignment.id)
                    .join(
                        collection_assignment_field_workers,
                        CollectionAssignment.id
                        == collection_assignment_field_workers.c.assignment_id,
                    )
                    .where(
                        collection_assignment_field_workers.c.field_worker_id
                        == worker.id,
                        CollectionAssignment.status.in_(
                            CollectionAssignmentService.ACTIVE_ASSIGNMENT_STATUSES
                        ),
                    )
                )

                if existing_worker_assignment:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field worker {worker.worker_code} already has an active assignment",
                    )

        # 7. Create assignment
        assignment = CollectionAssignment(
            assignment_code=f"ASN-{uuid4().hex[:10].upper()}",
            pickup_id=pickup.id,
            driver_id=driver.id,
            vehicle_id=vehicle.id,
            assigned_by_user_id=assigned_by_user_id,
            scheduled_date=data.scheduled_date,
            scheduled_time_slot=data.scheduled_time_slot,
            status=AssignmentStatus.ASSIGNED,
            notes=data.notes,
        )

        try:
            assignment = CollectionAssignmentRepository.create(
                db,
                assignment,
                data.field_worker_ids,
            )

            # 8. Update resource availability
            driver.availability = StaffAvailability.BUSY
            vehicle.status = VehicleStatus.ASSIGNED

            for worker in workers:
                worker.availability = StaffAvailability.BUSY

            # 9. Update pickup status
            pickup.status = PickupStatus.ASSIGNED

            db.commit()
            db.refresh(assignment)

            return assignment

        except Exception:
            db.rollback()
            raise

    # ---------------------------------------------------------
    # GET ASSIGNMENT
    # ---------------------------------------------------------

    @staticmethod
    def get_assignment(
        db: Session,
        assignment_id: UUID,
    ) -> CollectionAssignment:

        assignment = CollectionAssignmentRepository.get_by_id(
            db,
            assignment_id,
        )

        if not assignment:
            raise HTTPException(
                status_code=404,
                detail="Collection assignment not found",
            )

        return assignment

    # ---------------------------------------------------------
    # LIST ASSIGNMENTS
    # ---------------------------------------------------------

    @staticmethod
    def list_assignments(
        db: Session,
        status_filter=None,
        driver_id=None,
        vehicle_id=None,
        pickup_id=None,
    ):

        return CollectionAssignmentRepository.list_all(
            db,
            status=status_filter,
            driver_id=driver_id,
            vehicle_id=vehicle_id,
            pickup_id=pickup_id,
        )

    # ---------------------------------------------------------
    # PICKUP ASSIGNMENT HISTORY
    # ---------------------------------------------------------

    @staticmethod
    def get_pickup_assignment_history(
        db: Session,
        pickup_id: UUID,
    ):

        pickup = db.get(Pickup, pickup_id)

        if not pickup:
            raise HTTPException(
                status_code=404,
                detail="Pickup not found",
            )

        return CollectionAssignmentRepository.list_all(
            db,
            pickup_id=pickup_id,
        )

    # ---------------------------------------------------------
    # UPDATE / REASSIGN COLLECTION
    # ---------------------------------------------------------

    @staticmethod
    def update_assignment(
        db: Session,
        assignment_id: UUID,
        data,
    ):

        assignment = CollectionAssignmentService.get_assignment(
            db,
            assignment_id,
        )

        if assignment.status != AssignmentStatus.ASSIGNED:
            raise HTTPException(
                status_code=400,
                detail="Only assigned collections can be updated",
            )

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No update data provided",
            )

        old_driver = db.get(Driver, assignment.driver_id)
        old_vehicle = db.get(Vehicle, assignment.vehicle_id)

        old_workers = list(assignment.field_workers)

        new_driver_id = update_data.get(
            "driver_id",
            assignment.driver_id,
        )

        new_vehicle_id = update_data.get(
            "vehicle_id",
            assignment.vehicle_id,
        )

        new_worker_ids = update_data.get(
            "field_worker_ids",
            [worker.id for worker in old_workers],
        )

        pickup = db.get(Pickup, assignment.pickup_id)

        # Validate new driver
        driver = db.get(Driver, new_driver_id)

        if not driver or driver.status != StaffStatus.ACTIVE:
            raise HTTPException(
                status_code=400,
                detail="Selected driver does not exist or is inactive",
            )

        if new_driver_id != assignment.driver_id:

            if driver.availability != StaffAvailability.AVAILABLE:
                raise HTTPException(
                    status_code=400,
                    detail="Selected driver is not available",
                )

            conflict = CollectionAssignmentRepository.get_active_by_driver(
                db,
                new_driver_id,
            )

            if conflict and conflict.id != assignment.id:
                raise HTTPException(
                    status_code=400,
                    detail="Selected driver already has an active assignment",
                )

        # Validate new vehicle
        vehicle = db.get(Vehicle, new_vehicle_id)

        if not vehicle or not vehicle.is_active:
            raise HTTPException(
                status_code=400,
                detail="Selected vehicle does not exist or is inactive",
            )

        if vehicle.capacity_kg < pickup.estimated_quantity_kg:
            raise HTTPException(
                status_code=400,
                detail="Vehicle capacity is insufficient for this pickup",
            )

        if new_vehicle_id != assignment.vehicle_id:

            if vehicle.status != VehicleStatus.AVAILABLE:
                raise HTTPException(
                    status_code=400,
                    detail="Selected vehicle is not available",
                )

            conflict = CollectionAssignmentRepository.get_active_by_vehicle(
                db,
                new_vehicle_id,
            )

            if conflict and conflict.id != assignment.id:
                raise HTTPException(
                    status_code=400,
                    detail="Selected vehicle already has an active assignment",
                )

        # Validate new field workers
        workers = []

        if new_worker_ids:
            workers = db.scalars(
                select(FieldWorker).where(
                    FieldWorker.id.in_(new_worker_ids)
                )
            ).all()

            if len(workers) != len(new_worker_ids):
                raise HTTPException(
                    status_code=404,
                    detail="One or more field workers were not found",
                )

            for worker in workers:

                if worker.status != StaffStatus.ACTIVE:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Field worker {worker.worker_code} is inactive",
                    )

                if worker.id not in [
                    old_worker.id for old_worker in old_workers
                ]:

                    if worker.availability != StaffAvailability.AVAILABLE:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Field worker {worker.worker_code} is not available",
                        )

                    conflict = db.scalar(
                        select(CollectionAssignment.id)
                        .join(
                            collection_assignment_field_workers,
                            CollectionAssignment.id
                            == collection_assignment_field_workers.c.assignment_id,
                        )
                        .where(
                            collection_assignment_field_workers.c.field_worker_id
                            == worker.id,
                            CollectionAssignment.status.in_(
                                CollectionAssignmentService.ACTIVE_ASSIGNMENT_STATUSES
                            ),
                            CollectionAssignment.id != assignment.id,
                        )
                    )

                    if conflict:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Field worker {worker.worker_code} already has an active assignment",
                        )

        # Update assignment
        field_worker_ids = update_data.pop(
            "field_worker_ids",
            None,
        )

        try:
            CollectionAssignmentRepository.update(
                db,
                assignment,
                update_data,
                field_worker_ids,
            )

            # Release replaced resources
            if old_driver.id != driver.id:
                old_driver.availability = (
                    StaffAvailability.AVAILABLE
                    if old_driver.status == StaffStatus.ACTIVE
                    else StaffAvailability.UNAVAILABLE
                )

                driver.availability = StaffAvailability.BUSY

            if old_vehicle.id != vehicle.id:
                old_vehicle.status = (
                    VehicleStatus.AVAILABLE
                    if old_vehicle.is_active
                    else VehicleStatus.OUT_OF_SERVICE
                )

                vehicle.status = VehicleStatus.ASSIGNED

            new_worker_id_set = set(new_worker_ids)

            old_worker_id_set = {
                worker.id for worker in old_workers
            }

            for worker in old_workers:
                if worker.id not in new_worker_id_set:
                    worker.availability = (
                        StaffAvailability.AVAILABLE
                        if worker.status == StaffStatus.ACTIVE
                        else StaffAvailability.UNAVAILABLE
                    )

            for worker in workers:
                if worker.id not in old_worker_id_set:
                    worker.availability = StaffAvailability.BUSY

            db.commit()
            db.refresh(assignment)

            return assignment

        except Exception:
            db.rollback()
            raise

    # ---------------------------------------------------------
    # UPDATE ASSIGNMENT STATUS
    # ---------------------------------------------------------

    @staticmethod
    def update_assignment_status(
        db: Session,
        assignment_id: UUID,
        data,
    ):

        assignment = CollectionAssignmentService.get_assignment(
            db,
            assignment_id,
        )

        current_status = assignment.status
        new_status = data.status

        allowed_transitions = {
            AssignmentStatus.ASSIGNED: [
                AssignmentStatus.IN_PROGRESS,
                AssignmentStatus.CANCELLED,
            ],
            AssignmentStatus.IN_PROGRESS: [
                AssignmentStatus.COMPLETED,
            ],
            AssignmentStatus.COMPLETED: [],
            AssignmentStatus.CANCELLED: [],
        }

        if new_status not in allowed_transitions[current_status]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cannot change assignment from "
                    f"{current_status.value} to {new_status.value}"
                ),
            )

        if (
            new_status == AssignmentStatus.CANCELLED
            and not data.cancellation_reason
        ):
            raise HTTPException(
                status_code=400,
                detail="Cancellation reason is required",
            )

        pickup = db.get(Pickup, assignment.pickup_id)
        driver = db.get(Driver, assignment.driver_id)
        vehicle = db.get(Vehicle, assignment.vehicle_id)

        assignment.status = new_status

        if new_status == AssignmentStatus.IN_PROGRESS:
            assignment.started_at = CollectionAssignmentService.now()
            pickup.status = PickupStatus.IN_PROGRESS

        elif new_status == AssignmentStatus.COMPLETED:
            assignment.completed_at = CollectionAssignmentService.now()
            pickup.status = PickupStatus.COMPLETED

        elif new_status == AssignmentStatus.CANCELLED:
            assignment.cancelled_at = CollectionAssignmentService.now()
            assignment.cancellation_reason = data.cancellation_reason
            pickup.status = PickupStatus.SCHEDULED

        # Release resources when assignment ends
        if new_status in [
            AssignmentStatus.COMPLETED,
            AssignmentStatus.CANCELLED,
        ]:

            if driver:
                driver.availability = (
                    StaffAvailability.AVAILABLE
                    if driver.status == StaffStatus.ACTIVE
                    else StaffAvailability.UNAVAILABLE
                )

            if vehicle and vehicle.is_active:
                vehicle.status = VehicleStatus.AVAILABLE

            for worker in assignment.field_workers:
                worker.availability = (
                    StaffAvailability.AVAILABLE
                    if worker.status == StaffStatus.ACTIVE
                    else StaffAvailability.UNAVAILABLE
                )

        try:
            db.commit()
            db.refresh(assignment)
            return assignment

        except Exception:
            db.rollback()
            raise
