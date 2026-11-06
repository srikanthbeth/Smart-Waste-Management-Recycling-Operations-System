
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.driver import Driver
from models.user import User
from schemas.driver import DriverCreate, DriverUpdate, DriverStatusUpdate
from repositories.driver_repository import DriverRepository


class DriverService:

    @staticmethod
    def create_driver(db: Session, data: DriverCreate) -> Driver:
        user = db.get(User, data.user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        role = user.role.value if hasattr(user.role, "value") else str(user.role)

        if role.lower() != "driver":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected user must have the Driver role",
            )

        if DriverRepository.get_by_user_id(db, data.user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This user already has a driver profile",
            )

        if DriverRepository.get_by_code(db, data.driver_code):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Driver code already exists",
            )

        if DriverRepository.get_by_license(db, data.license_number):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="License number already exists",
            )

        driver = Driver(**data.model_dump())
        return DriverRepository.create(db, driver)

    @staticmethod
    def get_driver(db: Session, driver_id: UUID) -> Driver:
        driver = DriverRepository.get_by_id(db, driver_id)

        if not driver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver not found",
            )

        return driver

    @staticmethod
    def get_my_profile(db: Session, user_id: UUID) -> Driver:
        driver = DriverRepository.get_by_user_id(db, user_id)

        if not driver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver profile not found",
            )

        return driver

    @staticmethod
    def list_drivers(
        db: Session,
        status_filter=None,
        availability=None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Driver]:
        return DriverRepository.list_all(
            db,
            status=status_filter,
            availability=availability,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def update_driver(
        db: Session,
        driver_id: UUID,
        data: DriverUpdate,
    ) -> Driver:
        driver = DriverService.get_driver(db, driver_id)

        changes = data.model_dump(exclude_unset=True)

        if not changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update data provided",
            )

        if driver.status == "retired":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Retired drivers cannot be updated",
            )

        if "license_number" in changes:
            existing = DriverRepository.get_by_license(
                db, changes["license_number"]
            )
            if existing and existing.id != driver.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="License number already exists",
                )

        for key, value in changes.items():
            setattr(driver, key, value)

        return DriverRepository.update(db, driver)

    @staticmethod
    def update_status(
        db: Session,
        driver_id: UUID,
        data: DriverStatusUpdate,
    ) -> Driver:
        driver = DriverService.get_driver(db, driver_id)

        if driver.status.value == "retired":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Retired driver status cannot be changed",
            )

        driver.status = data.status

        if data.availability is not None:
            driver.availability = data.availability

        if data.status in {
            driver.status.__class__.INACTIVE,
            driver.status.__class__.SUSPENDED,
            driver.status.__class__.ON_LEAVE,
        }:
            driver.availability = driver.availability.__class__.UNAVAILABLE

        return DriverRepository.update(db, driver)
