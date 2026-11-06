from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from core.constants import WasteDisposalMethod, WasteDisposalStatus


class WasteDisposalCreate(BaseModel):
    processing_id: UUID

    disposal_method: WasteDisposalMethod

    disposal_site: str = Field(
        min_length=2,
        max_length=255,
    )

    disposal_quantity_kg: Decimal = Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
    )

    remarks: Optional[str] = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("disposal_site")
    @classmethod
    def validate_disposal_site(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Disposal site cannot be empty")

        return value

    @field_validator("remarks")
    @classmethod
    def validate_remarks(cls, value):
        if value is not None:
            value = value.strip()

        return value


class WasteDisposalResponse(BaseModel):
    id: UUID
    disposal_number: str

    processing_id: UUID
    recycling_center_id: UUID
    waste_category_id: UUID

    disposal_method: WasteDisposalMethod
    disposal_site: str
    disposal_quantity_kg: Decimal

    status: WasteDisposalStatus

    disposed_by_user_id: UUID
    disposed_at: datetime

    remarks: Optional[str]

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)