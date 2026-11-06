from uuid import UUID

from sqlalchemy.orm import Session

from models.waste_segregation import WasteSegregation


class WasteSegregationRepository:

    @staticmethod
    def create(
        db: Session,
        segregation: WasteSegregation,
    ) -> WasteSegregation:
        db.add(segregation)
        db.commit()
        db.refresh(segregation)

        return segregation

    @staticmethod
    def get_by_id(
        db: Session,
        segregation_id: UUID,
    ) -> WasteSegregation | None:
        return (
            db.query(WasteSegregation)
            .filter(WasteSegregation.id == segregation_id)
            .first()
        )

    @staticmethod
    def get_by_transfer(
        db: Session,
        transfer_id: UUID,
    ) -> list[WasteSegregation]:
        return (
            db.query(WasteSegregation)
            .filter(
                WasteSegregation.transfer_id == transfer_id
            )
            .order_by(WasteSegregation.segregated_at.desc())
            .all()
        )

    @staticmethod
    def list_all(
        db: Session,
        recycling_center_id: UUID | None = None,
        transfer_id: UUID | None = None,
        waste_category_id: UUID | None = None,
        status=None,
        segregated_by_user_id: UUID | None = None,
    ) -> list[WasteSegregation]:

        query = db.query(WasteSegregation)

        if recycling_center_id is not None:
            query = query.filter(
                WasteSegregation.recycling_center_id
                == recycling_center_id
            )

        if transfer_id is not None:
            query = query.filter(
                WasteSegregation.transfer_id == transfer_id
            )

        if waste_category_id is not None:
            query = query.filter(
                WasteSegregation.waste_category_id
                == waste_category_id
            )

        if status is not None:
            query = query.filter(
                WasteSegregation.status == status
            )

        if segregated_by_user_id is not None:
            query = query.filter(
                WasteSegregation.segregated_by_user_id
                == segregated_by_user_id
            )

        return (
            query
            .order_by(WasteSegregation.segregated_at.desc())
            .all()
        )

    @staticmethod
    def update(
        db: Session,
        segregation: WasteSegregation,
        update_data: dict,
    ) -> WasteSegregation:

        for field, value in update_data.items():
            setattr(segregation, field, value)

        db.commit()
        db.refresh(segregation)

        return segregation

    @staticmethod
    def delete(
        db: Session,
        segregation: WasteSegregation,
    ) -> None:
        db.delete(segregation)
        db.commit()