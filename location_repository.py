
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.location import Location


class LocationRepository:

    @staticmethod
    def create(db: Session, location_data: dict) -> Location:
        location = Location(**location_data)
        db.add(location)
        db.commit()
        db.refresh(location)
        return location

    @staticmethod
    def get_by_id(db: Session, location_id: UUID) -> Location | None:
        return db.scalar(
            select(Location).where(Location.id == location_id)
        )

    @staticmethod
    def get_by_code(db: Session, code: str) -> Location | None:
        return db.scalar(
            select(Location).where(Location.code == code)
        )

    @staticmethod
    def list_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        location_type=None,
        status=None,
        parent_id=None,
    ) -> list[Location]:

        query = select(Location)

        if location_type is not None:
            query = query.where(
                Location.location_type == location_type
            )

        if status is not None:
            query = query.where(Location.status == status)

        if parent_id is not None:
            query = query.where(Location.parent_id == parent_id)

        query = (
            query
            .order_by(Location.name.asc())
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(query).all())

    @staticmethod
    def has_children(db: Session, location_id: UUID) -> bool:
        return db.scalar(
            select(Location.id)
            .where(Location.parent_id == location_id)
            .limit(1)
        ) is not None

    @staticmethod
    def update(
        db: Session,
        location: Location,
        update_data: dict,
    ) -> Location:
        for key, value in update_data.items():
            setattr(location, key, value)

        db.commit()
        db.refresh(location)
        return location
