
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import (
    WasteTransferStatus,
    PickupStatus,
    RecyclingCenterStatus,
    VehicleStatus,
)

from models.waste_transfer import WasteTransfer
from models.pickup import Pickup
from models.collection_tracking import CollectionTracking
from models.location import Location
from models.recycling_center import RecyclingCenter
from models.waste_category import WasteCategory
from models.vehicle import Vehicle

from repositories.waste_transfer_repository import (
    WasteTransferRepository,
)


class WasteTransferService:

    @staticmethod
    def _validate_references(
        db: Session,
        data: dict,
    ) -> None:

        pickup = db.get(Pickup, data["pickup_id"])

        if not pickup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pickup not found",
            )

        if pickup.status != PickupStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only completed pickups can be transferred",
            )

        if data.get("collection_tracking_id") is not None:
            tracking = db.get(
                CollectionTracking,
                data["collection_tracking_id"],
            )

            if not tracking:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Collection tracking record not found",
                )

            if tracking.pickup_id != pickup.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Collection tracking does not belong to this pickup",
                )

        location = db.get(
            Location,
            data["source_location_id"],
        )

        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source location not found",
            )

        center = db.get(
            RecyclingCenter,
            data["recycling_center_id"],
        )

        if not center:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recycling center not found",
            )

        if center.status != RecyclingCenterStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recycling center is not active",
            )

        if not center.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recycling center is not available",
            )

        category = db.get(
            WasteCategory,
            data["waste_category_id"],
        )

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste category not found",
            )

        vehicle = db.get(
            Vehicle,
            data["vehicle_id"],
        )

        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found",
            )

        if vehicle.status != VehicleStatus.AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vehicle is not available",
            )

    @staticmethod
    def _generate_transfer_number() -> str:
        timestamp = datetime.now(timezone.utc).strftime(
            "%Y%m%d%H%M%S%f"
        )
        return f"WT-{timestamp}"

    @staticmethod
    def create_transfer(
        db: Session,
        data: dict,
        current_user,
    ) -> WasteTransfer:

        transfer_data = data.copy()

        WasteTransferService._validate_references(
            db,
            transfer_data,
        )

        existing_transfer = (
            WasteTransferRepository.get_by_pickup(
                db,
                transfer_data["pickup_id"],
            )
        )

        if existing_transfer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A transfer already exists for this pickup",
            )

        transfer_data["transfer_number"] = (
            WasteTransferService._generate_transfer_number()
        )

        transfer_data["created_by_user_id"] = current_user.id
        transfer_data["status"] = WasteTransferStatus.PENDING

        return WasteTransferRepository.create(
            db,
            transfer_data,
        )

    @staticmethod
    def get_transfer(
        db: Session,
        transfer_id: UUID,
    ) -> WasteTransfer:

        transfer = WasteTransferRepository.get_by_id(
            db,
            transfer_id,
        )

        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Waste transfer not found",
            )

        return transfer

    @staticmethod
    def list_transfers(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        recycling_center_id: UUID | None = None,
        pickup_id: UUID | None = None,
        transfer_status: WasteTransferStatus | None = None,
        created_by_user_id: UUID | None = None,
    ) -> list[WasteTransfer]:

        return WasteTransferRepository.list_all(
            db=db,
            skip=skip,
            limit=limit,
            recycling_center_id=recycling_center_id,
            pickup_id=pickup_id,
            status=transfer_status,
            created_by_user_id=created_by_user_id,
        )

    @staticmethod
    def update_transfer(
        db: Session,
        transfer_id: UUID,
        data: dict,
    ) -> WasteTransfer:

        transfer = WasteTransferService.get_transfer(
            db,
            transfer_id,
        )

        if transfer.status != WasteTransferStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending transfers can be updated",
            )

        update_data = data.copy()

        if "recycling_center_id" in update_data:
            center = db.get(
                RecyclingCenter,
                update_data["recycling_center_id"],
            )

            if not center:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Recycling center not found",
                )

            if (
                center.status != RecyclingCenterStatus.ACTIVE
                or not center.is_available
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Recycling center is not available",
                )

        if "vehicle_id" in update_data:
            vehicle = db.get(
                Vehicle,
                update_data["vehicle_id"],
            )

            if not vehicle:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vehicle not found",
                )

            if vehicle.status != VehicleStatus.AVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vehicle is not available",
                )

        return WasteTransferRepository.update(
            db,
            transfer,
            update_data,
        )

    @staticmethod
    def dispatch_transfer(
        db: Session,
        transfer_id: UUID,
        remarks: str | None = None,
    ) -> WasteTransfer:

        transfer = WasteTransferService.get_transfer(
            db,
            transfer_id,
        )

        if transfer.status != WasteTransferStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending transfers can be dispatched",
            )

        transfer.status = WasteTransferStatus.DISPATCHED
        transfer.dispatched_at = datetime.now(timezone.utc)

        if remarks:
            transfer.remarks = remarks

        return WasteTransferRepository.update(
            db,
            transfer,
            {},
        )

    @staticmethod
    def mark_in_transit(
        db: Session,
        transfer_id: UUID,
    ) -> WasteTransfer:

        transfer = WasteTransferService.get_transfer(
            db,
            transfer_id,
        )

        if transfer.status != WasteTransferStatus.DISPATCHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only dispatched transfers can be marked in transit",
            )

        return WasteTransferRepository.update(
            db,
            transfer,
            {
                "status": WasteTransferStatus.IN_TRANSIT,
            },
        )

    @staticmethod
    def receive_transfer(
        db: Session,
        transfer_id: UUID,
        received_quantity_kg: Decimal,
        current_user,
        remarks: str | None = None,
    ) -> WasteTransfer:

        transfer = WasteTransferService.get_transfer(
            db,
            transfer_id,
        )

        if transfer.status != WasteTransferStatus.IN_TRANSIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only in-transit transfers can be received",
            )

        if received_quantity_kg <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Received quantity must be greater than zero",
            )

        if received_quantity_kg > transfer.quantity_kg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Received quantity cannot exceed dispatched quantity",
            )

        new_status = (
            WasteTransferStatus.RECEIVED
            if received_quantity_kg == transfer.quantity_kg
            else WasteTransferStatus.PARTIALLY_RECEIVED
        )

        update_data = {
            "received_quantity_kg": received_quantity_kg,
            "status": new_status,
            "received_at": datetime.now(timezone.utc),
            "received_by_user_id": current_user.id,
        }

        if remarks:
            update_data["remarks"] = remarks

        return WasteTransferRepository.update(
            db,
            transfer,
            update_data,
        )

    @staticmethod
    def reject_transfer(
        db: Session,
        transfer_id: UUID,
        remarks: str | None = None,
    ) -> WasteTransfer:

        transfer = WasteTransferService.get_transfer(
            db,
            transfer_id,
        )

        if transfer.status not in (
            WasteTransferStatus.DISPATCHED,
            WasteTransferStatus.IN_TRANSIT,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only dispatched or in-transit transfers can be rejected",
            )

        if not remarks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Remarks are required when rejecting a transfer",
            )

        return WasteTransferRepository.update(
            db,
            transfer,
            {
                "status": WasteTransferStatus.REJECTED,
                "remarks": remarks,
            },
        )

    @staticmethod
    def cancel_transfer(
        db: Session,
        transfer_id: UUID,
        remarks: str | None = None,
    ) -> WasteTransfer:

        transfer = WasteTransferService.get_transfer(
            db,
            transfer_id,
        )

        if transfer.status not in (
            WasteTransferStatus.PENDING,
            WasteTransferStatus.DISPATCHED,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending or dispatched transfers can be cancelled",
            )

        return WasteTransferRepository.update(
            db,
            transfer,
            {
                "status": WasteTransferStatus.CANCELLED,
                "remarks": remarks or transfer.remarks,
            },
        )
