
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from models.recycling_center import RecyclingCenter
from models.waste_category import WasteCategory


class RecyclingCenterRepository:

    @staticmethod
    def create(
        db: Session,
        data: dict,
    ) -> RecyclingCenter:
        category_ids = data.pop(
            "accepted_waste_category_ids",
            [],
        )

        center = RecyclingCenter(**data)

        if category_ids:
            categories = db.scalars(
                select(WasteCategory).where(
                    WasteCategory.id.in_(category_ids)
                )
            ).all()

            center.accepted_waste_categories = list(categories)

        db.add(center)
        db.commit()
        db.refresh(center)

        return center

    @staticmethod
    def get_by_id(
        db: Session,
        center_id: UUID,
    ) -> RecyclingCenter | None:
        statement = (
            select(RecyclingCenter)
            .options(
                selectinload(
                    RecyclingCenter.accepted_waste_categories
                )
            )
            .where(RecyclingCenter.id == center_id)
        )

        return db.scalar(statement)

    @staticmethod
    def get_by_code(
        db: Session,
        code: str,
    ) -> RecyclingCenter | None:
        return db.scalar(
            select(RecyclingCenter).where(
                RecyclingCenter.code == code
            )
        )

    @staticmethod
    def get_by_name(
        db: Session,
        name: str,
    ) -> RecyclingCenter | None:
        return db.scalar(
            select(RecyclingCenter).where(
                RecyclingCenter.name == name
            )
        )

    @staticmethod
    def list_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RecyclingCenter]:
        statement = (
            select(RecyclingCenter)
            .options(
                selectinload(
                    RecyclingCenter.accepted_waste_categories
                )
            )
            .order_by(RecyclingCenter.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def update(
        db: Session,
        center: RecyclingCenter,
        data: dict,
    ) -> RecyclingCenter:
        category_ids = data.pop(
            "accepted_waste_category_ids",
            None,
        )

        for field, value in data.items():
            setattr(center, field, value)

        if category_ids is not None:
            categories = db.scalars(
                select(WasteCategory).where(
                    WasteCategory.id.in_(category_ids)
                )
            ).all()

            center.accepted_waste_categories = list(categories)

        db.commit()
        db.refresh(center)

        return center

    @staticmethod
    def delete(
        db: Session,
        center: RecyclingCenter,
    ) -> None:
        db.delete(center)
        db.commit()

    @staticmethod
    def get_categories(
        db: Session,
        category_ids: list[UUID],
    ) -> list[WasteCategory]:
        if not category_ids:
            return []

        return list(
            db.scalars(
                select(WasteCategory).where(
                    WasteCategory.id.in_(category_ids)
                )
            ).all()
        )
