from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import (
    WasteTransferStatus,
    WasteSegregationStatus,
)

from models.waste_transfer import WasteTransfer
from models.waste_segregation import WasteSegregation

from repositories.waste_segregation_repository import (
    WasteSegregationRepository,
)


class WasteSegregationService:

    @staticmethod
    def _validate_transfer(
        db: Session,
        transfer_id: UUID,
    ) -> WasteTransfer:

        transfer = db.query(WasteTransfer).filter(
            WasteTransfer.id == transfer_id
        ).first()

        if transfer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste transfer not found",
            )

        if transfer.status not in (
            WasteTransferStatus.RECEIVED,
            WasteTransferStatus.PARTIALLY_RECEIVED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only received transfers can be segregated",
            )

        if (
            transfer.received_quantity_kg is None
            or transfer.received_quantity_kg <= 0
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transfer has no received quantity",
            )

        return transfer

    @staticmethod
    def _validate_center_category(
        db: Session,
        transfer: WasteTransfer,
    ) -> None:

        from models.recycling_center import RecyclingCenter

        center = db.query(RecyclingCenter).filter(
            RecyclingCenter.id == transfer.recycling_center_id
        ).first()

        if center is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recycling center not found",
            )

        accepted_category_ids = {
            category.id
            for category in center.accepted_waste_categories
        }

        if transfer.waste_category_id not in accepted_category_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recycling center does not accept this waste category",
            )

    @staticmethod
    def _calculate_status(
        incoming_quantity: Decimal,
        recyclable_quantity: Decimal,
        non_recyclable_quantity: Decimal,
        contaminated_quantity: Decimal,
    ) -> WasteSegregationStatus:

        segregated_quantity = (
            recyclable_quantity
            + non_recyclable_quantity
            + contaminated_quantity
        )

        if segregated_quantity == incoming_quantity:
            return WasteSegregationStatus.COMPLETED

        return WasteSegregationStatus.PARTIALLY_SEGREGATED

    @staticmethod
    def create_segregation(
        db: Session,
        data,
        current_user,
    ) -> WasteSegregation:

        transfer = WasteSegregationService._validate_transfer(
            db,
            data.transfer_id,
        )

        WasteSegregationService._validate_center_category(
            db,
            transfer,
        )

        previous_records = (
            WasteSegregationRepository.get_by_transfer(
                db,
                transfer.id,
            )
        )

        previously_recorded_quantity = sum(
            (
                record.incoming_quantity_kg
                for record in previous_records
            ),
            Decimal("0.00"),
        )

        available_quantity = (
            Decimal(str(transfer.received_quantity_kg))
            - previously_recorded_quantity
        )

        if data.incoming_quantity_kg > available_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Incoming quantity exceeds the remaining "
                    "unsegregated transfer quantity"
                ),
            )

        segregation_status = (
            WasteSegregationService._calculate_status(
                data.incoming_quantity_kg,
                data.recyclable_quantity_kg,
                data.non_recyclable_quantity_kg,
                data.contaminated_quantity_kg,
            )
        )

        segregation = WasteSegregation(
            transfer_id=transfer.id,
            recycling_center_id=transfer.recycling_center_id,
            waste_category_id=transfer.waste_category_id,
            incoming_quantity_kg=data.incoming_quantity_kg,
            recyclable_quantity_kg=data.recyclable_quantity_kg,
            non_recyclable_quantity_kg=data.non_recyclable_quantity_kg,
            contaminated_quantity_kg=data.contaminated_quantity_kg,
            status=segregation_status,
            segregated_by_user_id=current_user.id,
            remarks=data.remarks,
        )

        return WasteSegregationRepository.create(
            db,
            segregation,
        )

    @staticmethod
    def get_segregation(
        db: Session,
        segregation_id: UUID,
    ) -> WasteSegregation:

        segregation = WasteSegregationRepository.get_by_id(
            db,
            segregation_id,
        )

        if segregation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste segregation record not found",
            )

        return segregation

    @staticmethod
    def list_segregations(
        db: Session,
        recycling_center_id: UUID | None = None,
        transfer_id: UUID | None = None,
        waste_category_id: UUID | None = None,
        segregation_status: WasteSegregationStatus | None = None,
        segregated_by_user_id: UUID | None = None,
    ):

        return WasteSegregationRepository.list_all(
            db=db,
            recycling_center_id=recycling_center_id,
            transfer_id=transfer_id,
            waste_category_id=waste_category_id,
            status=segregation_status,
            segregated_by_user_id=segregated_by_user_id,
        )

    @staticmethod
    def get_transfer_history(
        db: Session,
        transfer_id: UUID,
    ):

        transfer = db.query(WasteTransfer).filter(
            WasteTransfer.id == transfer_id
        ).first()

        if transfer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste transfer not found",
            )

        return WasteSegregationRepository.get_by_transfer(
            db,
            transfer_id,
        )

    @staticmethod
    def update_segregation(
        db: Session,
        segregation_id: UUID,
        data,
    ) -> WasteSegregation:

        segregation = (
            WasteSegregationService.get_segregation(
                db,
                segregation_id,
            )
        )

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No update fields provided",
            )

        recyclable = update_data.get(
            "recyclable_quantity_kg",
            segregation.recyclable_quantity_kg,
        )

        non_recyclable = update_data.get(
            "non_recyclable_quantity_kg",
            segregation.non_recyclable_quantity_kg,
        )

        contaminated = update_data.get(
            "contaminated_quantity_kg",
            segregation.contaminated_quantity_kg,
        )

        total = (
            recyclable
            + non_recyclable
            + contaminated
        )

        if total > segregation.incoming_quantity_kg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Total segregated quantity cannot exceed "
                    "incoming quantity"
                ),
            )

        update_data["status"] = (
            WasteSegregationService._calculate_status(
                segregation.incoming_quantity_kg,
                recyclable,
                non_recyclable,
                contaminated,
            )
        )

        return WasteSegregationRepository.update(
            db,
            segregation,
            update_data,
        )