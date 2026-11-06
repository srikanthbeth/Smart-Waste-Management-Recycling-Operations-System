
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from core.constants import WasteTransferStatus


class WasteTransferCreate(BaseModel):

    pickup_id: UUID

    collection_tracking_id: UUID | None = None

    source_location_id: UUID

    recycling_center_id: UUID

    waste_category_id: UUID

    vehicle_id: UUID

    quantity_kg: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class WasteTransferUpdate(BaseModel):

    recycling_center_id: UUID | None = None

    vehicle_id: UUID | None = None

    quantity_kg: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError(
                "At least one field must be provided"
            )

        for field_name in (
            "recycling_center_id",
            "vehicle_id",
            "quantity_kg",
        ):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(
                    f"{field_name} cannot be null"
                )

        return self


class WasteTransferStatusUpdate(BaseModel):

    status: WasteTransferStatus


class WasteTransferDispatch(BaseModel):

    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )


class WasteTransferReceive(BaseModel):

    received_quantity_kg: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    remarks: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value


class WasteTransferResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: UUID

    transfer_number: str

    pickup_id: UUID

    collection_tracking_id: UUID | None

    source_location_id: UUID

    recycling_center_id: UUID

    waste_category_id: UUID

    vehicle_id: UUID

    quantity_kg: Decimal

    received_quantity_kg: Decimal | None

    status: WasteTransferStatus

    dispatched_at: datetime | None

    received_at: datetime | None

    created_by_user_id: UUID

    received_by_user_id: UUID | None

    remarks: str | None

    created_at: datetime

    updated_at: datetime
