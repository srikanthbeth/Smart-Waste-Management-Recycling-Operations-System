
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import (
    WasteProcessingStatus,
    WasteSegregationStatus,
)

from models.waste_processing import WasteProcessing
from models.waste_segregation import WasteSegregation

from repositories.waste_processing_repository import (
    WasteProcessingRepository,
)


class WasteProcessingService:

    @staticmethod
    def _get_segregation(db: Session, segregation_id: UUID):
        segregation = db.get(
            WasteSegregation,
            segregation_id,
        )

        if not segregation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste segregation record not found",
            )

        if segregation.status not in (
            WasteSegregationStatus.COMPLETED,
            WasteSegregationStatus.PARTIALLY_SEGREGATED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Waste segregation record is not available",
            )

        if segregation.recyclable_quantity_kg <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No recyclable waste is available for processing",
            )

        return segregation

    @staticmethod
    def _calculate_status(
        processing_quantity: Decimal,
        output_quantity: Decimal,
        residual_quantity: Decimal,
        processing_loss: Decimal,
    ):
        accounted_quantity = (
            output_quantity
            + residual_quantity
            + processing_loss
        )

        if accounted_quantity == processing_quantity:
            return WasteProcessingStatus.COMPLETED

        return WasteProcessingStatus.PARTIALLY_PROCESSED

    @staticmethod
    def create_processing(
        db: Session,
        payload,
        current_user,
    ):
        segregation = WasteProcessingService._get_segregation(
            db,
            payload.segregation_id,
        )

        already_processed = (
            WasteProcessingRepository.get_total_processed_quantity(
                db,
                segregation.id,
            )
        )

        available_quantity = (
            Decimal(str(segregation.recyclable_quantity_kg))
            - Decimal(str(already_processed))
        )

        requested_quantity = Decimal(
            str(payload.processing_quantity_kg)
        )

        if requested_quantity > available_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Processing quantity exceeds available "
                    f"recyclable waste. Available: "
                    f"{available_quantity} kg"
                ),
            )

        output_quantity = Decimal(
            str(payload.output_quantity_kg)
        )

        residual_quantity = Decimal(
            str(payload.residual_quantity_kg)
        )

        processing_loss = Decimal(
            str(payload.processing_loss_kg)
        )

        processing_number = (
            f"WP-{uuid4().hex[:12].upper()}"
        )

        processing = WasteProcessing(
            processing_number=processing_number,
            segregation_id=segregation.id,
            recycling_center_id=segregation.recycling_center_id,
            waste_category_id=segregation.waste_category_id,
            processing_method=payload.processing_method,
            processing_quantity_kg=requested_quantity,
            output_quantity_kg=output_quantity,
            residual_quantity_kg=residual_quantity,
            processing_loss_kg=processing_loss,
            status=WasteProcessingService._calculate_status(
                requested_quantity,
                output_quantity,
                residual_quantity,
                processing_loss,
            ),
            processed_by_user_id=current_user.id,
            remarks=payload.remarks,
        )

        return WasteProcessingRepository.create(
            db,
            processing,
        )

    @staticmethod
    def get_processing(
        db: Session,
        processing_id: UUID,
    ):
        processing = WasteProcessingRepository.get_by_id(
            db,
            processing_id,
        )

        if not processing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste processing record not found",
            )

        return processing

    @staticmethod
    def list_processings(
        db: Session,
        segregation_id=None,
        recycling_center_id=None,
        waste_category_id=None,
        processing_status=None,
        processing_method=None,
        processed_by_user_id=None,
    ):
        return WasteProcessingRepository.list_all(
            db=db,
            segregation_id=segregation_id,
            recycling_center_id=recycling_center_id,
            waste_category_id=waste_category_id,
            processing_status=processing_status,
            processing_method=processing_method,
            processed_by_user_id=processed_by_user_id,
        )

    @staticmethod
    def get_segregation_history(
        db: Session,
        segregation_id: UUID,
    ):
        WasteProcessingService._get_segregation(
            db,
            segregation_id,
        )

        return (
            WasteProcessingRepository.get_segregation_history(
                db,
                segregation_id,
            )
        )
