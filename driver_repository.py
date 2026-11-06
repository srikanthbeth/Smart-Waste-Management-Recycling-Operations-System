
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.driver import Driver


class DriverRepository:

    @staticmethod
    def create(db: Session, driver: Driver) -> Driver:
        db.add(driver)
        db.commit()
        db.refresh(driver)
        return driver

    @staticmethod
    def get_by_id(db: Session, driver_id: UUID) -> Driver | None:
        return db.scalar(
            select(Driver).where(Driver.id == driver_id)
        )

    @staticmethod
    def get_by_user_id(db: Session, user_id: UUID) -> Driver | None:
        return db.scalar(
            select(Driver).where(Driver.user_id == user_id)
        )

    @staticmethod
    def get_by_code(db: Session, driver_code: str) -> Driver | None:
        return db.scalar(
            select(Driver).where(Driver.driver_code == driver_code)
        )

    @staticmethod
    def get_by_license(db: Session, license_number: str) -> Driver | None:
        return db.scalar(
            select(Driver).where(Driver.license_number == license_number)
        )

    @staticmethod
    def list_all(
        db: Session,
        status=None,
        availability=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Driver]:
        query = select(Driver)

        if status is not None:
            query = query.where(Driver.status == status)

        if availability is not None:
            query = query.where(Driver.availability == availability)

        query = query.order_by(Driver.created_at.desc())
        query = query.offset(skip).limit(limit)

        return list(db.scalars(query).all())

    @staticmethod
    def update(db: Session, driver: Driver) -> Driver:
        db.commit()
        db.refresh(driver)
        return driver

    @staticmethod
    def delete(db: Session, driver: Driver) -> None:
        db.delete(driver)
        db.commit()
