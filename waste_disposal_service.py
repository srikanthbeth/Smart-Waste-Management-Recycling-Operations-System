from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import (
    WasteDisposalStatus,
)

from models.waste_disposal import WasteDisposal
from models.waste_processing import WasteProcessing

from repositories.waste_disposal_repository import (
    WasteDisposalRepository,
)


class WasteDisposalService:

    @staticmethod
    def create_disposal(
        db: Session,
        payload,
        current_user,
    ):
        processing = db.query(WasteProcessing).filter(
            WasteProcessing.id == payload.processing_id
        ).with_for_update().first()

        if not processing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste processing record not found",
            )

        residual_quantity = Decimal(
            str(processing.residual_quantity_kg or 0)
        )

        if residual_quantity <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This processing record has no residual waste available for disposal",
            )

        already_disposed = Decimal(
            str(
                WasteDisposalRepository.get_total_disposed_quantity(
                    db,
                    processing.id,
                )
            )
        )

        available_quantity = residual_quantity - already_disposed

        requested_quantity = Decimal(
            str(payload.disposal_quantity_kg)
        )

        if requested_quantity > available_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Disposal quantity exceeds available residual waste. "
                    f"Available quantity: {available_quantity} kg"
                ),
            )

        new_total = already_disposed + requested_quantity

        if new_total >= residual_quantity:
            disposal_status = WasteDisposalStatus.COMPLETED
        else:
            disposal_status = WasteDisposalStatus.PARTIALLY_DISPOSED

        disposal = WasteDisposal(
            disposal_number=f"WD-{uuid4().hex[:12].upper()}",
            processing_id=processing.id,
            recycling_center_id=processing.recycling_center_id,
            waste_category_id=processing.waste_category_id,
            disposal_method=payload.disposal_method,
            disposal_site=payload.disposal_site,
            disposal_quantity_kg=requested_quantity,
            status=disposal_status,
            disposed_by_user_id=current_user.id,
            remarks=payload.remarks,
        )

        return WasteDisposalRepository.create(db, disposal)

    @staticmethod
    def get_disposal(db: Session, disposal_id):
        disposal = WasteDisposalRepository.get_by_id(
            db,
            disposal_id,
        )

        if not disposal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste disposal record not found",
            )

        return disposal

    @staticmethod
    def list_disposals(
        db: Session,
        processing_id=None,
        recycling_center_id=None,
        disposal_method=None,
        disposal_status=None,
    ):
        return WasteDisposalRepository.list_all(
            db,
            processing_id=processing_id,
            recycling_center_id=recycling_center_id,
            disposal_method=disposal_method,
            status=disposal_status,
        )

    @staticmethod
    def get_processing_history(db: Session, processing_id):
        processing = db.get(WasteProcessing, processing_id)

        if not processing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste processing record not found",
            )

        return WasteDisposalRepository.get_processing_history(
            db,
            processing_id,
        )