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

from core.constants import WasteSegregationStatus


class WasteSegregationCreate(BaseModel):
    transfer_id: UUID

    incoming_quantity_kg: Decimal = Field(
        ...,
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    recyclable_quantity_kg: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    non_recyclable_quantity_kg: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    contaminated_quantity_kg: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    remarks: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def validate_total_quantity(self):
        total = (
            self.recyclable_quantity_kg
            + self.non_recyclable_quantity_kg
            + self.contaminated_quantity_kg
        )

        if total > self.incoming_quantity_kg:
            raise ValueError(
                "Total segregated quantity cannot exceed incoming quantity"
            )

        return self


class WasteSegregationUpdate(BaseModel):
    recyclable_quantity_kg: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    non_recyclable_quantity_kg: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    contaminated_quantity_kg: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    remarks: str | None = Field(
        default=None,
        max_length=1000,
    )

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def validate_update_fields(self):
        if not self.model_fields_set:
            raise ValueError(
                "At least one field must be provided for update"
            )

        return self


class WasteSegregationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transfer_id: UUID
    recycling_center_id: UUID
    waste_category_id: UUID

    incoming_quantity_kg: Decimal
    recyclable_quantity_kg: Decimal
    non_recyclable_quantity_kg: Decimal
    contaminated_quantity_kg: Decimal

    status: WasteSegregationStatus

    segregated_by_user_id: UUID
    segregated_at: datetime

    remarks: str | None

    created_at: datetime
    updated_at: datetime