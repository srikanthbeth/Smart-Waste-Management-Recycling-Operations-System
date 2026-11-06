from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.waste_transfer import WasteTransfer
from core.constants import WasteTransferStatus


class WasteTransferRepository:

    @staticmethod
    def create(
        db: Session,
        data: dict,
    ) -> WasteTransfer:

        transfer = WasteTransfer(**data)

        db.add(transfer)
        db.commit()
        db.refresh(transfer)

        return transfer

    @staticmethod
    def get_by_id(
        db: Session,
        transfer_id: UUID,
    ) -> WasteTransfer | None:

        return db.scalar(
            select(WasteTransfer).where(
                WasteTransfer.id == transfer_id
            )
        )

    @staticmethod
    def get_by_number(
        db: Session,
        transfer_number: str,
    ) -> WasteTransfer | None:

        return db.scalar(
            select(WasteTransfer).where(
                WasteTransfer.transfer_number == transfer_number
            )
        )

    @staticmethod
    def get_by_pickup(
        db: Session,
        pickup_id: UUID,
    ) -> WasteTransfer | None:

        return db.scalar(
            select(WasteTransfer)
            .where(WasteTransfer.pickup_id == pickup_id)
            .order_by(WasteTransfer.created_at.desc())
        )

    @staticmethod
    def list_all(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        recycling_center_id: UUID | None = None,
        pickup_id: UUID | None = None,
        status: WasteTransferStatus | None = None,
        created_by_user_id: UUID | None = None,
    ) -> list[WasteTransfer]:

        statement = select(WasteTransfer)

        if recycling_center_id is not None:
            statement = statement.where(
                WasteTransfer.recycling_center_id
                == recycling_center_id
            )

        if pickup_id is not None:
            statement = statement.where(
                WasteTransfer.pickup_id == pickup_id
            )

        if status is not None:
            statement = statement.where(
                WasteTransfer.status == status
            )

        if created_by_user_id is not None:
            statement = statement.where(
                WasteTransfer.created_by_user_id
                == created_by_user_id
            )

        statement = (
            statement
            .order_by(WasteTransfer.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def update(
        db: Session,
        transfer: WasteTransfer,
        data: dict,
    ) -> WasteTransfer:

        for field, value in data.items():
            setattr(transfer, field, value)

        db.commit()
        db.refresh(transfer)

        return transfer

    @staticmethod
    def delete(
        db: Session,
        transfer: WasteTransfer,
    ) -> None:

        db.delete(transfer)
        db.commit()