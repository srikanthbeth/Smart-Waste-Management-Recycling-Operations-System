from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.waste_category import WasteCategory
from schemas.waste_category import (
    WasteCategoryCreate,
    WasteCategoryUpdate,
)


class WasteCategoryRepository:

    @staticmethod
    def create(
        db: Session,
        category_data: WasteCategoryCreate,
    ) -> WasteCategory:
        category = WasteCategory(
            **category_data.model_dump()
        )

        db.add(category)
        db.commit()
        db.refresh(category)

        return category

    @staticmethod
    def get_by_id(
        db: Session,
        category_id: UUID,
    ) -> WasteCategory | None:
        return db.scalar(
            select(WasteCategory).where(
                WasteCategory.id == category_id
            )
        )

    @staticmethod
    def get_by_code(
        db: Session,
        code: str,
    ) -> WasteCategory | None:
        return db.scalar(
            select(WasteCategory).where(
                WasteCategory.code == code
            )
        )

    @staticmethod
    def get_by_name(
        db: Session,
        name: str,
    ) -> WasteCategory | None:
        return db.scalar(
            select(WasteCategory).where(
                WasteCategory.name.ilike(name)
            )
        )

    @staticmethod
    def list_all(
        db: Session,
        status=None,
        is_recyclable: bool | None = None,
        is_hazardous: bool | None = None,
    ) -> list[WasteCategory]:
        statement = select(WasteCategory)

        if status is not None:
            statement = statement.where(
                WasteCategory.status == status
            )

        if is_recyclable is not None:
            statement = statement.where(
                WasteCategory.is_recyclable == is_recyclable
            )

        if is_hazardous is not None:
            statement = statement.where(
                WasteCategory.is_hazardous == is_hazardous
            )

        statement = statement.order_by(
            WasteCategory.name.asc()
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def update(
        db: Session,
        category: WasteCategory,
        update_data: WasteCategoryUpdate,
    ) -> WasteCategory:
        values = update_data.model_dump(exclude_unset=True)

        for field, value in values.items():
            setattr(category, field, value)

        db.commit()
        db.refresh(category)

        return category

    @staticmethod
    def update_status(
        db: Session,
        category: WasteCategory,
        status,
    ) -> WasteCategory:
        category.status = status

        db.commit()
        db.refresh(category)

        return category