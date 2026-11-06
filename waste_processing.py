
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

from core.constants import (
    WasteProcessingMethod,
    WasteProcessingStatus,
)


class WasteProcessingCreate(BaseModel):
    segregation_id: UUID

    processing_method: WasteProcessingMethod

    processing_quantity_kg: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    output_quantity_kg: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    residual_quantity_kg: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    processing_loss_kg: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    remarks: str | None = None

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value

    @model_validator(mode="after")
    def validate_processing_quantities(self):
        total = (
            self.output_quantity_kg
            + self.residual_quantity_kg
            + self.processing_loss_kg
        )

        if total > self.processing_quantity_kg:
            raise ValueError(
                "Output, residual, and processing loss "
                "cannot exceed processing quantity"
            )

        return self


class WasteProcessingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    processing_number: str
    segregation_id: UUID
    recycling_center_id: UUID
    waste_category_id: UUID

    processing_method: WasteProcessingMethod

    processing_quantity_kg: Decimal
    output_quantity_kg: Decimal
    residual_quantity_kg: Decimal
    processing_loss_kg: Decimal

    status: WasteProcessingStatus

    processed_by_user_id: UUID
    processed_at: datetime

    remarks: str | None

    created_at: datetime
    updated_at: datetime
