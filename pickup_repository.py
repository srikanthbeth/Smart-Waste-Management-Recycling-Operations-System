
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.constants import PickupStatus
from models.pickup import Pickup
from schemas.pickup import PickupCreate, PickupUpdate


class PickupRepository:

    @staticmethod
    def create(
        db: Session,
        customer_id: uuid.UUID,
        pickup_code: str,
        pickup_data: PickupCreate,
    ) -> Pickup:
        pickup = Pickup(
            customer_id=customer_id,
            pickup_code=pickup_code,
            **pickup_data.model_dump(),
        )

        db.add(pickup)
        db.commit()
        db.refresh(pickup)

        return pickup

    @staticmethod
    def get_by_id(
        db: Session,
        pickup_id: uuid.UUID,
    ) -> Pickup | None:
        return db.scalar(
            select(Pickup).where(
                Pickup.id == pickup_id
            )
        )

    @staticmethod
    def get_by_code(
        db: Session,
        pickup_code: str,
    ) -> Pickup | None:
        return db.scalar(
            select(Pickup).where(
                Pickup.pickup_code == pickup_code
            )
        )

    @staticmethod
    def list_all(
        db: Session,
        customer_id: uuid.UUID | None = None,
        pickup_status: PickupStatus | None = None,
        location_id: uuid.UUID | None = None,
        preferred_date: date | None = None,
        city: str | None = None,
    ) -> list[Pickup]:
        statement = select(Pickup)

        if customer_id is not None:
            statement = statement.where(
                Pickup.customer_id == customer_id
            )

        if pickup_status is not None:
            statement = statement.where(
                Pickup.status == pickup_status
            )

        if location_id is not None:
            statement = statement.where(
                Pickup.location_id == location_id
            )

        if preferred_date is not None:
            statement = statement.where(
                Pickup.preferred_date == preferred_date
            )

        if city is not None:
            statement = statement.where(
                Pickup.city.ilike(f"%{city}%")
            )

        statement = statement.order_by(
            Pickup.requested_at.desc()
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def list_by_customer(
        db: Session,
        customer_id: uuid.UUID,
    ) -> list[Pickup]:
        return PickupRepository.list_all(
            db,
            customer_id=customer_id,
        )

    @staticmethod
    def update(
        db: Session,
        pickup: Pickup,
        update_data: PickupUpdate,
    ) -> Pickup:
        values = update_data.model_dump(
            exclude_unset=True,
        )

        for field, value in values.items():
            setattr(pickup, field, value)

        db.commit()
        db.refresh(pickup)

        return pickup

    @staticmethod
    def update_status(
        db: Session,
        pickup: Pickup,
        pickup_status: PickupStatus,
        rejection_reason: str | None = None,
        cancellation_reason: str | None = None,
    ) -> Pickup:
        pickup.status = pickup_status
        pickup.rejection_reason = rejection_reason
        pickup.cancellation_reason = cancellation_reason

        db.commit()
        db.refresh(pickup)

        return pickup
