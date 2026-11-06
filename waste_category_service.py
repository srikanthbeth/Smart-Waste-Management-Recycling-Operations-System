from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import WasteCategoryStatus
from repositories.waste_category_repository import WasteCategoryRepository
from schemas.waste_category import (
    WasteCategoryCreate,
    WasteCategoryUpdate,
)


class WasteCategoryService:

    @staticmethod
    def create_category(
        db: Session,
        category_data: WasteCategoryCreate,
    ):
        existing_code = WasteCategoryRepository.get_by_code(
            db,
            category_data.code,
        )

        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Waste category code already exists",
            )

        existing_name = WasteCategoryRepository.get_by_name(
            db,
            category_data.name,
        )

        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Waste category name already exists",
            )

        try:
            return WasteCategoryRepository.create(
                db,
                category_data,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Waste category name or code already exists",
            )

    @staticmethod
    def get_category(
        db: Session,
        category_id: UUID,
    ):
        category = WasteCategoryRepository.get_by_id(
            db,
            category_id,
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste category not found",
            )

        return category

    @staticmethod
    def list_categories(
        db: Session,
        category_status: WasteCategoryStatus | None = None,
        is_recyclable: bool | None = None,
        is_hazardous: bool | None = None,
    ):
        return WasteCategoryRepository.list_all(
            db,
            status=category_status,
            is_recyclable=is_recyclable,
            is_hazardous=is_hazardous,
        )

    @staticmethod
    def update_category(
        db: Session,
        category_id: UUID,
        update_data: WasteCategoryUpdate,
    ):
        category = WasteCategoryService.get_category(
            db,
            category_id,
        )

        values = update_data.model_dump(exclude_unset=True)

        if not values:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update fields provided",
            )

        if "name" in values and values["name"] is not None:
            existing_name = WasteCategoryRepository.get_by_name(
                db,
                values["name"],
            )

            if existing_name and existing_name.id != category.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Waste category name already exists",
                )

        if "code" in values and values["code"] is not None:
            existing_code = WasteCategoryRepository.get_by_code(
                db,
                values["code"],
            )

            if existing_code and existing_code.id != category.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Waste category code already exists",
                )

        try:
            return WasteCategoryRepository.update(
                db,
                category,
                update_data,
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Waste category name or code already exists",
            )

    @staticmethod
    def update_category_status(
        db: Session,
        category_id: UUID,
        category_status: WasteCategoryStatus,
    ):
        category = WasteCategoryService.get_category(
            db,
            category_id,
        )

        return WasteCategoryRepository.update_status(
            db,
            category,
            category_status,
        )