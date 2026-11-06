
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.recycling_center import RecyclingCenter
from models.location import Location
from models.user import User
from models.waste_category import WasteCategory
from core.constants import RecyclingCenterStatus

from repositories.recycling_center_repository import (
    RecyclingCenterRepository,
)


class RecyclingCenterService:

    @staticmethod
    def _validate_location(
        db: Session,
        location_id: UUID,
    ) -> None:
        location = db.get(Location, location_id)

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found",
            )

    @staticmethod
    def _validate_manager(
        db: Session,
        manager_user_id: UUID | None,
    ) -> None:
        if manager_user_id is None:
            return

        manager = db.get(User, manager_user_id)

        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager user not found",
            )

    @staticmethod
    def _validate_categories(
        db: Session,
        category_ids: list[UUID],
    ) -> list[WasteCategory]:
        if not category_ids:
            return []

        categories = RecyclingCenterRepository.get_categories(
            db,
            category_ids,
        )

        if len(categories) != len(category_ids):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more waste categories not found",
            )

        return categories

    @staticmethod
    def create_center(
        db: Session,
        data: dict,
    ) -> RecyclingCenter:
        center_data = data.copy()

        name = center_data["name"].strip()
        code = center_data["code"].strip()

        if RecyclingCenterRepository.get_by_name(db, name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recycling center name already exists",
            )

        if RecyclingCenterRepository.get_by_code(db, code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recycling center code already exists",
            )

        RecyclingCenterService._validate_location(
            db,
            center_data["location_id"],
        )

        RecyclingCenterService._validate_manager(
            db,
            center_data.get("manager_user_id"),
        )

        category_ids = center_data.get(
            "accepted_waste_category_ids",
            [],
        )

        RecyclingCenterService._validate_categories(
            db,
            category_ids,
        )

        return RecyclingCenterRepository.create(
            db,
            center_data,
        )

    @staticmethod
    def get_center(
        db: Session,
        center_id: UUID,
    ) -> RecyclingCenter:
        center = RecyclingCenterRepository.get_by_id(
            db,
            center_id,
        )

        if not center:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recycling center not found",
            )

        return center

    @staticmethod
    def list_centers(
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RecyclingCenter]:
        return RecyclingCenterRepository.list_all(
            db,
            skip,
            limit,
        )

    @staticmethod
    def update_center(
        db: Session,
        center_id: UUID,
        data: dict,
    ) -> RecyclingCenter:
        center = RecyclingCenterService.get_center(
            db,
            center_id,
        )

        update_data = data.copy()

        if "name" in update_data:
            name = update_data["name"].strip()

            existing = RecyclingCenterRepository.get_by_name(
                db,
                name,
            )

            if existing and existing.id != center.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Recycling center name already exists",
                )

        if "code" in update_data:
            code = update_data["code"].strip()

            existing = RecyclingCenterRepository.get_by_code(
                db,
                code,
            )

            if existing and existing.id != center.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Recycling center code already exists",
                )

        if update_data.get("location_id") is not None:
            RecyclingCenterService._validate_location(
                db,
                update_data["location_id"],
            )

        if (
            "manager_user_id" in update_data
            and update_data["manager_user_id"] is not None
        ):
            RecyclingCenterService._validate_manager(
                db,
                update_data["manager_user_id"],
            )

        if "accepted_waste_category_ids" in update_data:
            category_ids = update_data[
                "accepted_waste_category_ids"
            ]

            RecyclingCenterService._validate_categories(
                db,
                category_ids,
            )

        return RecyclingCenterRepository.update(
            db,
            center,
            update_data,
        )

    @staticmethod
    def update_center_status(
        db: Session,
        center_id: UUID,
        new_status: RecyclingCenterStatus,
        is_available: bool | None = None,
    ) -> RecyclingCenter:
        center = RecyclingCenterService.get_center(
            db,
            center_id,
        )

        center.status = new_status

        if is_available is not None:
            center.is_available = is_available
        elif new_status != RecyclingCenterStatus.ACTIVE:
            center.is_available = False
        else:
            center.is_available = True

        db.commit()
        db.refresh(center)

        return center

    @staticmethod
    def delete_center(
        db: Session,
        center_id: UUID,
    ) -> None:
        center = RecyclingCenterService.get_center(
            db,
            center_id,
        )

        RecyclingCenterRepository.delete(
            db,
            center,
        )
