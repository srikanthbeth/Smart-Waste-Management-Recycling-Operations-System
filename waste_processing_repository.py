
from uuid import UUID

from sqlalchemy.orm import Session

from models.waste_processing import WasteProcessing


class WasteProcessingRepository:

    @staticmethod
    def create(db: Session, processing: WasteProcessing):
        db.add(processing)
        db.commit()
        db.refresh(processing)
        return processing

    @staticmethod
    def get_by_id(db: Session, processing_id: UUID):
        return (
            db.query(WasteProcessing)
            .filter(WasteProcessing.id == processing_id)
            .first()
        )

    @staticmethod
    def get_by_number(db: Session, processing_number: str):
        return (
            db.query(WasteProcessing)
            .filter(
                WasteProcessing.processing_number
                == processing_number
            )
            .first()
        )

    @staticmethod
    def list_all(
        db: Session,
        segregation_id=None,
        recycling_center_id=None,
        waste_category_id=None,
        processing_status=None,
        processing_method=None,
        processed_by_user_id=None,
    ):
        query = db.query(WasteProcessing)

        if segregation_id is not None:
            query = query.filter(
                WasteProcessing.segregation_id == segregation_id
            )

        if recycling_center_id is not None:
            query = query.filter(
                WasteProcessing.recycling_center_id
                == recycling_center_id
            )

        if waste_category_id is not None:
            query = query.filter(
                WasteProcessing.waste_category_id
                == waste_category_id
            )

        if processing_status is not None:
            query = query.filter(
                WasteProcessing.status == processing_status
            )

        if processing_method is not None:
            query = query.filter(
                WasteProcessing.processing_method
                == processing_method
            )

        if processed_by_user_id is not None:
            query = query.filter(
                WasteProcessing.processed_by_user_id
                == processed_by_user_id
            )

        return query.order_by(
            WasteProcessing.processed_at.desc()
        ).all()

    @staticmethod
    def get_segregation_history(
        db: Session,
        segregation_id: UUID,
    ):
        return (
            db.query(WasteProcessing)
            .filter(
                WasteProcessing.segregation_id == segregation_id
            )
            .order_by(WasteProcessing.processed_at.desc())
            .all()
        )

    @staticmethod
    def get_total_processed_quantity(
        db: Session,
        segregation_id: UUID,
    ):
        from sqlalchemy import func

        result = (
            db.query(
                func.coalesce(
                    func.sum(
                        WasteProcessing.processing_quantity_kg
                    ),
                    0,
                )
            )
            .filter(
                WasteProcessing.segregation_id == segregation_id
            )
            .scalar()
        )

        return result
