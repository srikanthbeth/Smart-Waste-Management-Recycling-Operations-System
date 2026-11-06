
from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import (
    CustomerStatus,
    LocationStatus,
    PickupStatus,
    UserRole,
    WasteCategoryStatus,
)
from models.customer import Customer
from models.location import Location
from models.pickup import Pickup
from models.user import User
from models.waste_category import WasteCategory
from repositories.pickup_repository import PickupRepository
from schemas.pickup import PickupCreate, PickupStatusUpdate, PickupUpdate


MANAGEMENT_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.OPERATIONS_MANAGER,
    UserRole.COLLECTION_SUPERVISOR,
}

ACTIVE_DUPLICATE_STATUSES = {
    PickupStatus.REQUESTED,
    PickupStatus.APPROVED,
    PickupStatus.SCHEDULED,
    PickupStatus.ASSIGNED,
    PickupStatus.IN_PROGRESS,
}

ALLOWED_TRANSITIONS = {
    PickupStatus.REQUESTED: {
        PickupStatus.APPROVED,
        PickupStatus.REJECTED,
        PickupStatus.CANCELLED,
    },
    PickupStatus.APPROVED: {
        PickupStatus.SCHEDULED,
        PickupStatus.CANCELLED,
    },
    PickupStatus.SCHEDULED: {
        PickupStatus.ASSIGNED,
        PickupStatus.CANCELLED,
    },
    PickupStatus.ASSIGNED: {
        PickupStatus.IN_PROGRESS,
        PickupStatus.CANCELLED,
    },
    PickupStatus.IN_PROGRESS: {
        PickupStatus.COMPLETED,
    },
    PickupStatus.COMPLETED: set(),
    PickupStatus.CANCELLED: set(),
    PickupStatus.REJECTED: set(),
}


class PickupService:

    @staticmethod
    def get_customer_profile(
        db: Session,
        current_user: User,
    ) -> Customer:
        if current_user.role != UserRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only customers can request waste pickup",
            )

        customer = db.query(Customer).filter(
            Customer.user_id == current_user.id
        ).first()

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer profile not found. Create your profile first.",
            )

        if customer.status != CustomerStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your customer profile is not active",
            )

        return customer

    @staticmethod
    def validate_waste_category(
        db: Session,
        waste_category_id: UUID,
    ) -> WasteCategory:
        category = db.get(WasteCategory, waste_category_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste category not found",
            )

        if category.status != WasteCategoryStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected waste category is inactive",
            )

        return category

    @staticmethod
    def validate_location(
        db: Session,
        location_id: UUID | None,
    ):
        if location_id is None:
            return

        location = db.get(Location, location_id)

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pickup location not found",
            )

        if (
            location.status != LocationStatus.ACTIVE
            or not location.is_active
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected pickup location is inactive",
            )

    @staticmethod
    def create_pickup(
        db: Session,
        current_user: User,
        pickup_data: PickupCreate,
    ) -> Pickup:
        customer = PickupService.get_customer_profile(
            db,
            current_user,
        )

        PickupService.validate_waste_category(
            db,
            pickup_data.waste_category_id,
        )

        PickupService.validate_location(
            db,
            pickup_data.location_id,
        )

        if pickup_data.preferred_date <= date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Preferred pickup date must be in the future",
            )

        existing_pickups = PickupRepository.list_by_customer(
            db,
            customer.id,
        )

        for existing in existing_pickups:
            if (
                existing.preferred_date == pickup_data.preferred_date
                and existing.waste_category_id
                == pickup_data.waste_category_id
                and existing.status in ACTIVE_DUPLICATE_STATUSES
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "An active pickup request already exists "
                        "for this waste category and date"
                    ),
                )

        pickup_code = f"PICK-{uuid4().hex[:12].upper()}"

        try:
            return PickupRepository.create(
                db,
                customer.id,
                pickup_code,
                pickup_data,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Unable to create pickup request",
            )

    @staticmethod
    def get_pickup(
        db: Session,
        pickup_id: UUID,
    ) -> Pickup:
        pickup = PickupRepository.get_by_id(
            db,
            pickup_id,
        )

        if not pickup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pickup request not found",
            )

        return pickup

    @staticmethod
    def get_pickup_for_user(
        db: Session,
        pickup_id: UUID,
        current_user: User,
    ) -> Pickup:
        pickup = PickupService.get_pickup(
            db,
            pickup_id,
        )

        if current_user.role in MANAGEMENT_ROLES:
            return pickup

        customer = PickupService.get_customer_profile(
            db,
            current_user,
        )

        if pickup.customer_id != customer.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot access another customer's pickup request",
            )

        return pickup

    @staticmethod
    def list_my_pickups(
        db: Session,
        current_user: User,
    ) -> list[Pickup]:
        customer = PickupService.get_customer_profile(
            db,
            current_user,
        )

        return PickupRepository.list_by_customer(
            db,
            customer.id,
        )

    @staticmethod
    def list_pickups(
        db: Session,
        current_user: User,
        pickup_status: PickupStatus | None = None,
        location_id: UUID | None = None,
        preferred_date: date | None = None,
        city: str | None = None,
    ) -> list[Pickup]:
        if current_user.role not in MANAGEMENT_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to list all pickups",
            )

        return PickupRepository.list_all(
            db,
            pickup_status=pickup_status,
            location_id=location_id,
            preferred_date=preferred_date,
            city=city,
        )

    @staticmethod
    def update_pickup(
        db: Session,
        pickup_id: UUID,
        current_user: User,
        update_data: PickupUpdate,
    ) -> Pickup:
        pickup = PickupService.get_pickup_for_user(
            db,
            pickup_id,
            current_user,
        )

        if current_user.role != UserRole.CUSTOMER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the customer can edit this pickup request",
            )

        if pickup.status != PickupStatus.REQUESTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only requested pickups can be edited",
            )

        values = update_data.model_dump(exclude_unset=True)

        if not values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update fields provided",
            )

        if "waste_category_id" in values:
            if values["waste_category_id"] is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Waste category cannot be empty",
                )

            PickupService.validate_waste_category(
                db,
                values["waste_category_id"],
            )

        if "location_id" in values:
            PickupService.validate_location(
                db,
                values["location_id"],
            )

        try:
            return PickupRepository.update(
                db,
                pickup,
                update_data,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to update pickup request",
            )

    @staticmethod
    def update_pickup_status(
        db: Session,
        pickup_id: UUID,
        current_user: User,
        status_data: PickupStatusUpdate,
    ) -> Pickup:
        pickup = PickupService.get_pickup(
            db,
            pickup_id,
        )

        new_status = status_data.status

        if current_user.role == UserRole.CUSTOMER:
            customer = PickupService.get_customer_profile(
                db,
                current_user,
            )

            if pickup.customer_id != customer.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You cannot update another customer's pickup",
                )

            if new_status != PickupStatus.CANCELLED:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Customers can only cancel their own pickup requests",
                )

        elif current_user.role not in MANAGEMENT_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update pickup status",
            )

        allowed = ALLOWED_TRANSITIONS.get(
            pickup.status,
            set(),
        )

        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot change pickup status from "
                    f"{pickup.status.value} to {new_status.value}"
                ),
            )

        if (
            new_status == PickupStatus.REJECTED
            and not status_data.rejection_reason
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A rejection reason is required",
            )

        if (
            new_status == PickupStatus.CANCELLED
            and current_user.role != UserRole.CUSTOMER
            and not status_data.cancellation_reason
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A cancellation reason is required for staff cancellation",
            )

        if new_status == PickupStatus.COMPLETED:
            pickup.completed_at = datetime.now(timezone.utc)

        try:
            return PickupRepository.update_status(
                db,
                pickup,
                new_status,
                rejection_reason=status_data.rejection_reason,
                cancellation_reason=status_data.cancellation_reason,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to update pickup status",
            )
