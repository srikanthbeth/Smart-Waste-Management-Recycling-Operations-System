from sqlalchemy import func
from sqlalchemy.orm import Session

from models.waste_disposal import WasteDisposal


class WasteDisposalRepository:

    @staticmethod
    def create(db: Session, disposal: WasteDisposal):
        db.add(disposal)
        db.commit()
        db.refresh(disposal)
        return disposal

    @staticmethod
    def get_by_id(db: Session, disposal_id):
        return (
            db.query(WasteDisposal)
            .filter(WasteDisposal.id == disposal_id)
            .first()
        )

    @staticmethod
    def get_by_number(db: Session, disposal_number):
        return (
            db.query(WasteDisposal)
            .filter(WasteDisposal.disposal_number == disposal_number)
            .first()
        )

    @staticmethod
    def list_all(
        db: Session,
        processing_id=None,
        recycling_center_id=None,
        disposal_method=None,
        status=None,
    ):
        query = db.query(WasteDisposal)

        if processing_id:
            query = query.filter(
                WasteDisposal.processing_id == processing_id
            )

        if recycling_center_id:
            query = query.filter(
                WasteDisposal.recycling_center_id == recycling_center_id
            )

        if disposal_method:
            query = query.filter(
                WasteDisposal.disposal_method == disposal_method
            )

        if status:
            query = query.filter(
                WasteDisposal.status == status
            )

        return query.order_by(
            WasteDisposal.disposed_at.desc()
        ).all()

    @staticmethod
    def get_processing_history(db: Session, processing_id):
        return (
            db.query(WasteDisposal)
            .filter(WasteDisposal.processing_id == processing_id)
            .order_by(WasteDisposal.disposed_at.desc())
            .all()
        )

    @staticmethod
    def get_total_disposed_quantity(db: Session, processing_id):
        result = (
            db.query(
                func.coalesce(
                    func.sum(WasteDisposal.disposal_quantity_kg),
                    0,
                )
            )
            .filter(WasteDisposal.processing_id == processing_id)
            .scalar()
        )

        return result